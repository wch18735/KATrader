import os
import sys

from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtTest import *
from config.errorCode import *
from config.kiwoomType import *

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self.realType = RealType()

        ####### event loop를 실행하기 위한 변수 모음
        self.login_event_loop = QEventLoop()  # 로그인 요청용 이벤트 루프
        self.detail_account_event_loop = QEventLoop()  # 예수금 요청용 이벤트 루프
        self.calculator_event_loop = QEventLoop()
        #########################################

        ########### 전체 종목 관리
        self.all_stock_dict = {}
        ###########################

        ####### 계좌 관련된 변수
        self.account_stock_dict = {}
        self.not_account_stock_dict = {}
        self.account_num = None  # 계좌번호 담아줄 변수
        self.deposit = 0  # 예수금
        self.use_money = 0  # 실제 투자에 사용할 금액
        self.use_money_percent = 0.5  # 예수금에서 실제 사용할 비율
        self.output_deposit = 0  # 출력가능 금액
        self.total_profit_loss_money = 0  # 총평가손익금액
        self.total_profit_loss_rate = 0.0  # 총수익률(%)
        ########################################

        ######## 종목 정보 가져오기
        self.portfolio_stock_dict = {}
        self.jango_dict = {}
        ########################

        ########### 종목 분석 용
        self.calcul_data = []
        ##########################################

        ####### 요청 스크린 번호
        self.screen_my_info = "2000"  # 계좌 관련한 스크린 번호
        self.screen_calculation_stock = "4000"  # 계산용 스크린 번호
        self.screen_real_stock = "5000"  # 종목별 할당할 스크린 번호
        self.screen_meme_stock = "6000"  # 종목별 할당할 주문용 스크린 번호
        self.screen_start_stop_real = "1000"  # 장 시작/종료 실시간 스크린 번호
        ########################################

        ######### 초기 셋팅 함수들 바로 실행
        self.get_ocx_instance()  # OCX 방식을 파이썬에 사용할 수 있게 반환해 주는 함수 실행
        self.event_slots()  # 키움과 연결하기 위한 시그널 / 슬롯 모음
        self.real_event_slot()  # 실시간 이벤트 시그널 / 슬롯 연결
        self.signal_login_commConnect()  # 로그인 요청 함수 포함
        self.get_account_info()  # 계좌번호 가져오기

        self.detail_account_info()  # 예수금 요청 시그널 포함
        self.detail_account_mystock()  # 계좌평가잔고내역 가져오기
        QTimer.singleShot(5000, self.not_concluded_account)  # 5초 뒤에 미체결 종목들 가져오기 실행
        #########################################

        QTest.qWait(10000)
        self.read_code()
        self.screen_number_setting()

        QTest.qWait(5000)

        # 실시간 수신 관련 함수
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", self.screen_start_stop_real, '',
                         self.realType.REALTYPE['장시작시간']['장운영구분'], "0")

        for code in self.portfolio_stock_dict.keys():
            screen_num = self.portfolio_stock_dict[code]['스크린번호']
            fids = self.realType.REALTYPE['주식체결']['체결시간']
            self.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_num, code, fids, "1")



    #################### 로그인 메소드
    def get_ocx_instance(self):
        # QAxContainer: Handler that control OCX
        # Kiwoom OpenAPI is registered as KHOPENAPI.KHOpenAPICtrl.1
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def signal_login_commConnect(self):
        # self.dynamicCall(): 네트워크에 쿼리를 전송할 수 있도록 PyQt5가 제공하는 함수
        self.dynamicCall("CommConnect()")

        # 해당 프로그램은 단순하게 로그인 요청이 끝
        # 이후 프로그램이 진행될 때 Handler가 없는 오류가 발생
        # 따라서 이를 방지하기 위해 login_event_loop 생성 후 exec
        self.login_event_loop.exec_()

    #################### 슬롯 모음
    def event_slots(self):
        # Event Area
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.trdata_slot)
        self.OnReceiveMsg.connect(self.msg_slot)

    def real_event_slot(self):
        self.OnReceiveRealData.connect(self.realdata_slot)
        self.OnReceiveChejanData.connect(self.chejan_slot)

    def login_slot(self, err_code):
        if err_code == 0:
            print("로그인 성공")
            self.login_event_loop.exit() # block 된 Eventloop을 풀어주는 역할
        else:
            errors(err_code)

    def realdata_slot(self, sCode, sRealType, sRealData):
        '''
        :param sCode: 종목 코드
        :param sRealType: 한글로 나타남
        :param sRealData: 사용하는 경우 드뭄
        :return:
        '''
        print("실시간 데이터")
        print(sCode, sRealType)
        if sRealType == "장시작시간":
            fid = self.realType.REALTYPE[sRealType]['장운영구분']
            value = self.dynamicCall("GetCommRealData(QString, int)", sCode, fid)
            if value == '0':
                print("장 시작 전")
            elif value == '3':
                print("장 시작")
            elif value == '2':
                print("장 종료, 동시호가로 넘어감")
            elif value == '4':
                print("3시 30분 장 종료")

                for code in self.portfolio_stock_dict.keys():
                    self.dynamicCall("SetRealRemove(QString, QString)", self.portfolio_stock_dict[code]['스크린번호'], code)

                # 장 종료 후
                self.file_delete()
                self.calculator_fnc()

                sys.exit()

        elif sRealType == "주식체결":
            a = self.dynamicCall("GetCommRealData(QString, int)",
                                             sCode, self.realType.REALTYPE[sRealType]['체결시간'])
            b = self.dynamicCall("GetCommRealData(QString, int)",
                                             sCode, self.realType.REALTYPE[sRealType]['현재가'])
            c = self.dynamicCall("GetCommRealData(QString, int)",
                                             sCode, self.realType.REALTYPE[sRealType]['전일대비'])
            d = self.dynamicCall("GetCommRealData(QString, int)",
                                          sCode, self.realType.REALTYPE[sRealType]['등락율'])
            e = self.dynamicCall("GetCommRealData(QString, int)",
                                 sCode, self.realType.REALTYPE[sRealType]['(최우선)매도호가'])
            f = self.dynamicCall("GetCommRealData(QString, int)",
                                 sCode, self.realType.REALTYPE[sRealType]['(최우선)매수호가'])
            g = self.dynamicCall("GetCommRealData(QString, int)",
                                 sCode, self.realType.REALTYPE[sRealType]['거래량'])
            h = self.dynamicCall("GetCommRealData(QString, int)",
                                 sCode, self.realType.REALTYPE[sRealType]['누적거래량'])
            i = self.dynamicCall("GetCommRealData(QString, int)",
                                 sCode, self.realType.REALTYPE[sRealType]['고가'])
            j = self.dynamicCall("GetCommRealData(QString, int)",
                                 sCode, self.realType.REALTYPE[sRealType]['저가'])
            k = self.dynamicCall("GetCommRealData(QString, int)",
                                 sCode, self.realType.REALTYPE[sRealType]['시가'])

            b = abs(int(b)) # 현재가
            c = abs(int(c)) # 전일대비
            d = float(d)    # 등락율
            e = abs(int(e)) # (최우선)매도호가
            f = abs(int(f)) # (최우선)매수호가
            g = abs(int(g)) # 거래량
            h = abs(int(h)) # 누적거래량
            i = abs(int(i)) # 고가
            j = abs(int(j)) # 저가
            k = abs(int(k)) # 시가

            if sCode not in self.portfolio_stock_dict:
                self.portfolio_stock_dict.update({sCode:{}})

            self.portfolio_stock_dict[sCode].update({"체결시간": a})
            self.portfolio_stock_dict[sCode].update({"현재가": b})
            self.portfolio_stock_dict[sCode].update({"전일대비": c})
            self.portfolio_stock_dict[sCode].update({"등락율": d})
            self.portfolio_stock_dict[sCode].update({"(최우선)매도호가": e})
            self.portfolio_stock_dict[sCode].update({"(최우선)매수호가": f})
            self.portfolio_stock_dict[sCode].update({"거래량": g})
            self.portfolio_stock_dict[sCode].update({"누적거래량": h})
            self.portfolio_stock_dict[sCode].update({"고가": i})
            self.portfolio_stock_dict[sCode].update({"시가": j})
            self.portfolio_stock_dict[sCode].update({"저가": k})
            
            # 확인
            print(self.portfolio_stock_dict[sCode])

            # 계좌잔고평가내역에 존재 and 오늘 산 잔고에 없는 경우
            if sCode in self.account_stock_dict.keys() and sCode not in self.jango_dict.keys():
                print(f"{sCode} 신규매도")
                asd = self.account_stock_dict[sCode]
                
                # 수익률이 더 높을 때
                meme_rate = (b - asd['매입가']) / asd['매입가'] * 100

                if asd['매입가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):
                    order_success = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                                    ["신규매도", self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 2,
                                                    sCode, asd["매매가능수량"], 0, self.realType['거래구분']['시장가'], ""])

                    if order_success == 0:
                        print("매도주문 전달 성공")
                        del self.account_stock_dict[sCode]
                    else:
                        print("매도주문 전달 실패")

            # 오늘 산 잔고에 있을 경우
            elif sCode in self.jango_dict.keys():
                jd = self.jango_dict[sCode]
                meme_rate = (b - jd['매입단가']) / jd['매입단가'] * 100

                if jd['주문가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["신규매도", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 2, sCode, jd['주문가능수량'],
                         0, self.realType.SENDTYPE['거래구분']['시장가'], ""]
                    )

                    if order_success == 0:
                        print("매도주문 전달 성공")
                    else:
                        print("매도주문 전달 실패")

            # 등락율이 2.0% 이상이고 오늘 산 잔고에 없을 경우
            elif d > 2.0 and sCode not in self.jango_dict:
                print("매수조건 통과 %s " % sCode)

                result = (self.use_money * 0.1) / e
                quantity = int(result)

                order_success = self.dynamicCall(
                    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                    ["신규매수", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 1, sCode, quantity, e,
                     self.realType.SENDTYPE['거래구분']['지정가'], ""]
                )

                if order_success == 0:
                    print("매수주문 전달 성공")
                else:
                    print("매수주문 전달 실패")

            not_trade_list = list(self.not_account_stock_dict) # 미체결잔고 할당
            for order_num in not_trade_list:
                code = self.not_account_stock_dict[order_num]["종목코드"]
                price = self.not_account_stock_dict[order_num]["주문가격"]
                not_quantity = self.not_account_stock_dict[order_num]["미체결수량"]
                order_gubun = self.not_account_stock_dict[order_num]["주문구분"]


                if order_gubun == "매수" and not_quantity > 0 and e > price:
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["매수취소", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 3, code, 0, 0,
                         self.realType.SENDTYPE['거래구분']['지정가'], order_num]
                    )

                    if order_success == 0:
                        print("매수취소 전달 성공")
                    else:
                        print("매수취소 전달 실패")

                elif not_quantity == 0:
                    del self.not_account_stock_dict[order_num]

    def chejan_slot(self, sGubun, nItemCnt, sFIdList):
        if int(sGubun) == 0:  # 주문체결
            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목명'])
            origin_order_number = self.dynamicCall("GetChejanData(int)",
                                                   self.realType.REALTYPE['주문체결']['원주문번호'])  # 출력 : defaluse : "000000"
            order_number = self.dynamicCall("GetChejanData(int)",
                                            self.realType.REALTYPE['주문체결']['주문번호'])  # 출럭: 0115061 마지막 주문번호
            order_status = self.dynamicCall("GetChejanData(int)",
                                            self.realType.REALTYPE['주문체결']['주문상태'])  # 출력: 접수, 확인, 체결
            order_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문수량'])  # 출력 : 3
            order_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문가격'])  # 출력: 21000
            not_chegual_quan = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['미체결수량'])  # 출력: 15, default: 0
            order_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문구분'])  # 출력: -매도, +매수
            chegual_time_str = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['주문/체결시간'])  # 출력: '151028'
            chegual_price = self.dynamicCall("GetChejanData(int)",
                                             self.realType.REALTYPE['주문체결']['체결가'])  # 출력: 2110 default : ''

            stock_name = stock_name.strip()
            order_quan = int(order_quan)
            order_price = int(order_price)
            not_chegual_quan = int(not_chegual_quan)
            order_gubun = order_gubun.strip().lstrip('+').lstrip('-')

            if chegual_price == '':
                chegual_price = 0
            else:
                chegual_price = int(chegual_price)

            chegual_quantity = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['체결량'])  # 출력: 5 default : ''
            if chegual_quantity == '':
                chegual_quantity = 0
            else:
                chegual_quantity = int(chegual_quantity)

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['현재가'])  # 출력: -6000
            current_price = abs(int(current_price))

            first_sell_price = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['(최우선)매도호가'])  # 출력: -6010
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)",
                                               self.realType.REALTYPE['주문체결']['(최우선)매수호가'])  # 출력: -6000
            first_buy_price = abs(int(first_buy_price))

            ######## 새로 들어온 주문이면 주문번호 할당
            if order_number not in self.not_account_stock_dict.keys():
                self.not_account_stock_dict.update({order_number: {}})

            self.not_account_stock_dict[order_number].update({"종목코드": sCode})
            self.not_account_stock_dict[order_number].update({"주문번호": order_number})
            self.not_account_stock_dict[order_number].update({"종목명": stock_name})
            self.not_account_stock_dict[order_number].update({"주문상태": order_status})
            self.not_account_stock_dict[order_number].update({"주문수량": order_quan})
            self.not_account_stock_dict[order_number].update({"주문가격": order_price})
            self.not_account_stock_dict[order_number].update({"미체결수량": not_chegual_quan})
            self.not_account_stock_dict[order_number].update({"원주문번호": origin_order_number})
            self.not_account_stock_dict[order_number].update({"주문구분": order_gubun})
            self.not_account_stock_dict[order_number].update({"주문/체결시간": chegual_time_str})
            self.not_account_stock_dict[order_number].update({"체결가": chegual_price})
            self.not_account_stock_dict[order_number].update({"체결량": chegual_quantity})
            self.not_account_stock_dict[order_number].update({"현재가": current_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매도호가": first_sell_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매수호가": first_buy_price})

        elif int(sGubun) == 1:  # 잔고
            # 여기서 잔고 업데이트
            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목코드'])[1:]

            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목명'])
            stock_name = stock_name.strip()

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['현재가'])
            current_price = abs(int(current_price))

            stock_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['보유수량'])
            stock_quan = int(stock_quan)

            like_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['주문가능수량'])
            like_quan = int(like_quan)

            buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매입단가'])
            buy_price = abs(int(buy_price))

            total_buy_price = self.dynamicCall("GetChejanData(int)",
                                               self.realType.REALTYPE['잔고']['총매입가'])  # 계좌에 있는 종목의 총매입가
            total_buy_price = int(total_buy_price)

            first_sell_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매도호가'])
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매수호가'])
            first_buy_price = abs(int(first_buy_price))

            if sCode not in self.jango_dict.keys():
                self.jango_dict.update({sCode: {}})

            self.jango_dict[sCode].update({"현재가": current_price})
            self.jango_dict[sCode].update({"종목코드": sCode})
            self.jango_dict[sCode].update({"종목명": stock_name})
            self.jango_dict[sCode].update({"보유수량": stock_quan})
            self.jango_dict[sCode].update({"주문가능수량": like_quan})
            self.jango_dict[sCode].update({"매입단가": buy_price})
            self.jango_dict[sCode].update({"총매입가": total_buy_price})
            self.jango_dict[sCode].update({"(최우선)매도호가": first_sell_price})
            self.jango_dict[sCode].update({"(최우선)매수호가": first_buy_price})

            if stock_quan == 0:
                # 보유수량이 0이면 없앰
                del self.jango_dict[sCode]
                self.dynamicCall("SetRealRemove(QString, QString)", self.portfolio_stock_dict[sCode]['스크린번호'], sCode)


    # 송수신 메세지 get
    def msg_slot(self, sScrNo, sRQName, sTrCode, msg):
        print(f"[{sScrNo}][{sRQName}] 코드: {sTrCode} msg")

    # 파일 삭제
    def file_delete(self):
        if os.path.isfile("./files/condition_stock.txt"):
            os.remove("files/condition_stock.txt")


    ################## TR 데이터 수신 슬롯
    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        '''
        TR 요청을 받는 SLOT
        :param sScrNo: 스크린 번호
        :param sRQName: 사용자 지정 요청명
        :param sTrCode: TR코드
        :param sRecordName: 레코드명
        :param sPrevNext: 데이터 연속성 유무
        :return: None
        '''
        if sRQName == '예수금상세현황요청':
            deposit = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                        sTrCode, sRQName, 0, "예수금")
            possible_deposit = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                        sTrCode, sRQName, 0, "출금가능금액")

            self.use_money = int(deposit) * self.use_money_percent

            print("예수금 %s" % int(deposit))
            print("출금가능금액 %s" % int(possible_deposit))
            self.detail_account_event_loop.exit() # EventLoop 종료

        elif sRQName == "계좌평가잔고내역요청":
            total_buy_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총매입금액")
            total_buy_money = int(total_buy_money)
            print("총 매입 금액 %s" % total_buy_money)

            total_profit_loss_rate = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총수익률(%)")
            total_profit_loss_rate = float(total_profit_loss_rate)
            print("총수익률 (%%): %s" % total_profit_loss_rate)

            # 계좌 보유종목 수신
            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            cnt = 0
            for i in range(rows):
                code = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "종목번호")
                code_name = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "종목명")
                stock_quantity = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "보유수량")
                buy_price = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "매입가")
                learn_rate = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "수익률(%)")
                current_price = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "현재가")
                total_chegual_price = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "매입금액")
                possible_quantity = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "매매가능수량")

                code_name = code_name.strip()
                code = code.strip()[1:]
                stock_quantity = int(stock_quantity.strip())
                buy_price = int(buy_price.strip())
                learn_rate = float(learn_rate.strip())
                current_price = int(current_price.strip())
                total_chegual_price = int(total_chegual_price.strip())
                possible_quantity = int(possible_quantity.strip())

                if code in self.account_stock_dict:
                    pass
                else:
                    self.account_stock_dict.update({code: {}})

                self.account_stock_dict[code].update({"종목명": code_name})
                self.account_stock_dict[code].update({"보유수량": stock_quantity})
                self.account_stock_dict[code].update({"매입가": buy_price})
                self.account_stock_dict[code].update({"수익률(%)": learn_rate})
                self.account_stock_dict[code].update({"현재가": current_price})
                self.account_stock_dict[code].update({"매입금액": total_chegual_price})
                self.account_stock_dict[code].update({"매매가능수량": possible_quantity})
                # {"종목코드": {"종목명": 종목이름, "보유수량": 개수, ...}}
                cnt += 1

            print("계좌에 있는 종목 수 %s" % cnt) # 또는 len(self.account_stock_dict)

            # 20개 까지밖에 보여주지 않는다. 따라서 sPrevNext 값이 2가 나오면 한 번 더 요청해야 한다.
            # 요청 -> 반환 -> 요청 -> 반환 .. 순서로 진행
            # Slot 값으로 들어오는 sPrevNext=2 는 다음 페이지가 있다는 뜻
            # CommRqData 요청할 때 sPrevNext=2 는 다음 페이지를 요청
            if sPrevNext == "2":
                self.detail_account_mystock(sPrevNext="2")
            else:
                # 더 이상 다음 페이지가 없으므로 이벤트루프 종료
                self.detail_account_event_loop.exit()

        elif sRQName == "실시간미체결요청":
            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            for i in range(rows):
                code = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "종목번호")
                code_name = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "종목명")
                order_no = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "주문번호")
                order_status = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "주문상태") # 접수, 확인, 체결
                order_quantity = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "주문수량")
                order_price = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "주문가격")
                order_gubun = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "주문구분") # -매도, +매수, 정정주문, ..
                not_quantity = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "미체결수량")
                ok_quantity = self.dynamicCall("GetCommData(QString, QString)", sTrCode, sRQName, i, "체결량")

                code = code.strip()
                code_name = code_name.strip()
                order_no = int(order_no.strip())
                order_status = order_status.strip()
                order_quantity = int(order_quantity.strip())
                order_price = int(order_price.strip())
                order_gubun = order_gubun.strip().lstrip('+').lstrip('-')
                not_quantity = int(not_quantity.strip())
                ok_quantity = int(ok_quantity.strip())

                if order_no in self.not_account_stock_dict:
                    pass
                else:
                    self.not_account_stock_dict[order_no] = dict()

                # optimize_dict: 주소 값 공유
                optimize_dict = self.not_account_stock_dict[order_no]

                # 미체결은 당일 거래가 끝나면 모두 소멸
                optimize_dict.update({"종목번호": code})
                optimize_dict.update({"종목명": code_name})
                optimize_dict.update({"주문번호": order_no})
                optimize_dict.update({"주문상태": order_status})
                optimize_dict.update({"주문수량": order_quantity})
                optimize_dict.update({"주문가격": order_price})
                optimize_dict.update({"주문구분": order_gubun})
                optimize_dict.update({"미체결수량": not_quantity})
                optimize_dict.update({"체결량": ok_quantity})

            self.detail_account_event_loop.exit()

        elif sRQName == "주식일봉차트조회":
            code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "종목코드")
            print("%s 일봉데이터 요청" % code.strip())

            # 한 번 조회시 600일치까지 일봉 데이터 확보 가능
            cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            print("데이터 일 수 %s" % cnt)

            for i in range(cnt):
                data = []

                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                                 sTrCode, sRQName, i, "현재가")
                value = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                                 sTrCode, sRQName, i, "거래량")
                trading_value = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                                 sTrCode, sRQName, i, "거래대금")
                date = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                                 sTrCode, sRQName, i, "일자")
                start_price = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                                 sTrCode, sRQName, i, "시가")
                high_price = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                                 sTrCode, sRQName, i, "고가")
                low_price = self.dynamicCall("GetCommData(QString, QString, int, QString)",
                                                 sTrCode, sRQName, i, "저가")

                data.append("") # GetCommDataEx 형식과 맞추기 위해
                data.append(current_price.strip())
                data.append(value.strip())
                data.append(trading_value.strip())
                data.append(date.strip())
                data.append(start_price.strip())
                data.append(high_price.strip())
                data.append(low_price.strip())
                data.append("") # GetCommDataEx 형식과 맞추기 위해

                self.calcul_data.append(data.copy())

            if sPrevNext == "2":
                self.day_kiwoom_db(code=code.strip(), sPrevNext=sPrevNext)
            else:
                print(f"총 일 수 {len(self.calcul_data)}")
                pass_success = False
                if self.calcul_data == None or len(self.calcul_data) < 120:
                    pass_success = False
                else:
                    # 120일 이상
                    total_price = 0
                    for value in self.calcul_data[:120]:
                        # 추후에 여기를 Dictionary로 바꿔도 괜찮을 듯
                        total_price += int(value[1])
                    moving_average_price = total_price / 120

                    # 오늘자 주가가 120일 이평선에 걸쳐있는지 확인
                    bottom_stock_price = False
                    check_price = None
                    if int(self.calcul_data[0][7]) <= moving_average_price and moving_average_price <= int(self.calcul_data[0][6]):
                        # "오늘 주가 120 이평선 걸쳐있는 것 확인"
                        bottom_stock_price = True
                        check_price = int(self.calcul_data[0][6])

                    # 과거 일봉들이 120일 이평선보다 밑에 있는지 확인
                    # 일봉이 120일 이평선보다 위에 있으면 계산 진행
                    prev_price = None # 과거 일봉 저가
                    if bottom_stock_price:
                        moving_average_price_prev = 0
                        price_top_moving = False
                        idx = 1
                        while True:
                            if len(self.calcul_data[idx:]) < 120: # 120일치가 있는지 확인
                                print("120일치가 없음!")
                                break

                            total_price = 0
                            for value in self.calcul_data[idx:120+idx]:
                                total_price += int(value[1])
                            moving_average_price_prev = total_price / 120

                            if moving_average_price_prev <= int(self.calcul_data[idx][6]) and idx <= 20:
                                # 20일 동안 주가가 120일 이평선과 같거나 위에 있으면 조건 통과 X
                                price_top_moving = False
                                break

                            elif int(self.calcul_data[idx][7]) > moving_average_price_prev and idx > 20:
                                # 120일 이평선 위에 있는 일봉 확인됨
                                price_top_moving = True
                                prev_price = int(self.calcul_data[idx][7])
                                break

                            idx += 1

                        if price_top_moving == True:
                            # 해당 부분 이평선이 가장 최근 일자의 이평선 가격보다 낮은지 확인
                            if moving_average_price > moving_average_price_prev and check_price > prev_price:
                                # 포착된 이평선의 가격이 오늘자(최근 일자) 이평선 가격보다 낮은 것 확인 됨
                                # 포착된 부분의 일봉 저가가 일봉의 고가보다 낮은지 확인 됨
                                pass_success = True

                if pass_success:
                    # 조건 포착
                    code_name = self.dynamicCall("GetMasterCodeName(QString)", code)

                    with open("files/condition_stock.txt", "a", encoding="utf8") as f:
                        f.write(f"{code}\t{code_name}\t{str(self.calcul_data[0][1])}\n")

                self.calcul_data.clear()
                self.calculator_event_loop.exit()


    ############################### 요청
    def get_account_info(self):
        account_list = self.dynamicCall("GetLoginInfo(String)", "ACCNO")
        account_list = account_list.split(';')[:-1]
        self.account_num = account_list[0]
        print("나의 보유 계좌번호", self.account_num)

    def detail_account_info(self):
        print("예수금을 요청하는 부분")
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", '')
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "2")
        self.dynamicCall("CommRqData(QString, QString, int, QString)",
                         "예수금상세현황요청", "opw00001", "0", self.screen_my_info)
        # Return: ("요청이름", "TR번호", "preNext", "화면번호")
        # EventLoop 이용해 Block
        self.detail_account_event_loop.exec_()


    def detail_account_mystock(self, sPrevNext="0"):
        print("계좌평가 잔고내역 요청")
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "2")
        self.dynamicCall("CommRqData(QString, QString, int, QString)",
                         "계좌평가잔고내역요청", "opw00018", sPrevNext, self.screen_my_info)

        self.detail_account_event_loop.exec_()


    def not_concluded_account(self, sPrevNext="0"):
        print("미체결 요청")
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "전체종목구분", "0")
        self.dynamicCall("SetInputValue(QString, QString)", "매매구분", "0")
        self.dynamicCall("SetInputValue(QString, QString)", "체결구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "실시간미체결요청", "opt10075", sPrevNext, self.screen_my_info)
        self.detail_account_event_loop.exec_()


    def get_code_list_by_market(self, market_code):
        '''
        종목 코드 반환
        :param market_code:
        :return:
        '''
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_code)
        code_list = code_list.split(";")[:-1]
        return code_list


    def calculator_fnc(self):
        '''
        종목 분석 실행용 함수
        :return:
        '''
        code_list = self.get_code_list_by_market("10")
        print("코스닥 갯수 %s" % len(code_list))

        for idx, code in enumerate(code_list):
            self.dynamicCall("DisconnectRealData(QString)", self.screen_calculation_stock)
            print(f"{idx + 1} / {len(code_list)} : KOSDAQ Stock Code: {code} is updating...")
            self.day_kiwoom_db(code=code)


    def day_kiwoom_db(self, code=None, date=None, sPrevNext="0"):
        # Process 상에서 Thread, Process를 멈추지 않고 Wait
        QTest.qWait(3600)

        print("일봉데이터요청")
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")

        if date != None:
            self.dynamicCall("SetInputValue(QString, QString)", "기준일자", date)

        self.dynamicCall("CommRqData(QString, QString, int, QString)", "주식일봉차트조회", "opt10081", sPrevNext, self.screen_calculation_stock)
        self.calculator_event_loop.exec_()


    def read_code(self):
        print("파일 로드")
        if os.path.exists("files/condition_stock.txt"):
            with open("files/condition_stock.txt", "r", encoding="UTF-8") as f:
                lines = f.readlines()
                for line in lines:
                    if line != "":
                        stock_code, stock_name, stock_price = line.strip().split("\t")
                        stock_price = abs(int(stock_price))

                        self.portfolio_stock_dict.update({stock_code: {"종목명":stock_name, "현재가": stock_price}})


    def screen_number_setting(self):
        print("스크린 번호 세팅")
        screen_overwrite = list()

        # 계좌평가잔고내역에 있는 종목들
        for code in self.account_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 미체결에 있는 종목들
        for code in self.not_account_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 파일에 저장된 종목들
        for code in self.portfolio_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 스크린 번호 할당
        cnt = 0
        for code in screen_overwrite:
            temp_screen = int(self.screen_real_stock)
            trade_screen = int(self.screen_trade_stock)

            if (cnt % 50) == 0:
                temp_screen += 1
                self.screen_real_stock = str(temp_screen)

            if (trade_screen % 50) == 0:
                trade_screen += 1
                self.screen_trade_stock = str(trade_screen)

            if code in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict[code].update({"스크린번호": str(self.screen_real_stock)})
                self.portfolio_stock_dict[code].update({"주문용스크린번호": str(self.screen_trade_stock)})

            elif code not in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict.update(
                    {code: {"스크린번호": str(self.screen_real_stock), "주문용스크린번호": str(self.screen_trade_stock)}})

            cnt += 1