import os
import datetime

from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtTest import *
from config.error_code import *
from config.kiwoomType import *

####### 스크립트 구조 ########
# INIT
# LOGIN
# SLOT 모음
# TR 데이터 수신
# Request 모음
############################

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        print("Executed Kiwoom Class")

        ######### OCX 컨트롤러
        ######### 가장 중요!! 맨 위로 올려야 함
        self.get_ocx_instance()

        ########### 이벤트 루프 모음
        self.login_event_loop = QEventLoop()
        self.detail_account_event_loop = QEventLoop()
        self.calculator_event_loop = QEventLoop()
        
        ########### 로그인 요청
        self.signal_login_commConnect()
        
        ########### 계좌번호 요청
        self.get_account_info()

        ########### 변수 모음
        self.account_num = None
        self.account_stock_dict = dict()
        self.not_account_stock_dict = dict()

        ########### 클래스 모음
        self.realType = RealType()

        ########## 데이터 모음
        self.calcul_data = list()
        self.portfolio_stock_dict = dict()
        self.not_account_stock_dict = dict()

        ########## 스크린 번호 모음
        self.screen_start_stop_real = "1000"
        self.screen_account_info = "2000"
        self.screen_calcluation_stock = "4000"
        self.screen_real_stock = "5000"
        self.screen_trade_stock = "6000"

        ########### 계좌 관련 변수
        self.use_money = None
        self.use_money_percent = None
        self.use_portion = None

        ########### 이벤트 슬롯
        self.event_slots()
        self.real_event_slots()

        ########### 리퀘스트 모음
        self.detail_account_info()          # 예수금 요청
        self.detail_account_mystock()       # 계좌평가잔고내역 요청
        self.not_concluded_account()        # 미체결잔고내역 요청
        # self.calculator_fnc()               # 주식종목 분석
        self.read_code()                    # 저장된 종목 불러오기
        self.screen_number_setting()        # 스크린 번호 할당

        ########### 장 시작/마감 종료: 장이 마감되면 종료 Signal -> 실시간 Slot
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", self.screen_start_stop_real, '', self.realType.REALTYPE['장시작시간']['장운영구분'], "0")
        for code in self.portfolio_stock_dict.keys():
            screen_num = self.portfolio_stock_dict[code]['스크린번호']
            fids = self.realType.REALTYPE['주식체결']['체결시간']
            self.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                             screen_num, code, fids, "1") # 스크린번호에 종목코드 체결 정보를 받아오는 것을 등록("1")


    #################### 로그인 메소드
    def get_ocx_instance(self):
        # QAxContainer: Handler that control OCX
        # Kiwoom OpenAPI is registered as KHOPENAPI.KHOpenAPICtrl.1
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def signal_login_commConnect(self):
        # self.dynamicCall(): 네트워크에 쿼리를 전송할 수 있도록 PyQt5가 제공하는 함수
        self.dynamicCall("Commconnect()")

        # 해당 프로그램은 단순하게 로그인 요청이 끝
        # 이후 프로그램이 진행될 때 Handler가 없는 오류가 발생
        # 따라서 이를 방지하기 위해 login_event_loop 생성 후 exec
        self.login_event_loop.exec_()

    #################### 슬롯 모음
    def event_slots(self):
        # Event Area
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.trdata_slot)

    def real_event_slots(self):
        self.OnReceiveRealData.connect(self.realdata_slot)

    def login_slot(self, err_code):
        if err_code == 0:
            print("로그인 성공")

            # block 된 Eventloop을 풀어주는 역할
            self.login_event_loop.exit()
        else:
            errors(err_code)

    def realdata_slot(self, sCode, sRealType, sRealData):
        '''
        :param sCode: 종목 코드
        :param sRealType: 한글로 나타남
        :param sRealData: 사용하는 경우 드뭄
        :return: 
        '''
        print(sCode)
        if sRealType == "장시작시간":
            fid = self.realType.REALTYPE[sRealType]['장운영구분']
            value = self.dynamicCall("GetCommRealData(Qstring, int)", sCode, fid)
            if value == '0':
                print("장 시작 전")
            elif value == '3':
                print("장 시작")
            elif value == '2':
                print("장 종료, 동시호가로 넘어감")
            elif value == '4':
                print("3시 30분 장 종료")

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

            b = abs(int(b))
            c = abs(int(c))
            d = float(d)
            e = abs(int(e))
            f = abs(int(f))
            g = abs(int(g))
            h = abs(int(h))
            i = abs(int(i))
            j = abs(int(j))
            k = abs(int(k))

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

            print(self.portfolio_stock_dict[sCode])
            
            # 실시간 구매 여부 판단

            
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
            self.use_money = self.use_money / self.use_portion

            print("예수금 %s" % int(deposit))
            print("출금가능금액 %s" % int(possible_deposit))
            self.detail_account_info_event_loop.exit() # EventLoop 종료

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
                self.detail_account_mystock_event_loop.exit()

        elif sRQName=="실시간미체결요청":
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
                                                 sTrCode, sRQName, i, "종가")

                data.append("") # GetCommDataEx 형식과 맞추기 위해
                data.append(current_price.strip())
                data.append(value.strip())
                data.append(trading_value.strip())
                data.append(date.strip())
                data.append(start_price.strip())
                data.append(high_price.strip())
                data.append(low_price.strip())

                self.calcul_data.append(data.copy())

            if sPrevNext == "2":
                self.day_kiwoom_db(code=code.strip(), sPrevNext=sPrevNext)
            else:
                print("총 일 수 %s" % len(self.calcul_data))
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
                    if int(self.calcul_data[0][7] <= moving_average_price and moving_average_price <= self.calcul_data[0][6]):
                        print("오늘 주가 120 이평선 걸쳐있는 것 확인")
                        bottom_stock_price = True
                        check_price = int(self.calcul_data[0][6])

                    # 과거 일봉들이 120일 이평선보다 밑에 있는지 확인
                    # 일봉이 120일 이평선보다 위에 있으면 계산 진행

                    prev_price = None # 과거 일봉 저가
                    if bottom_stock_price == True:
                        moving_average_price_prev = 0
                        price_top_moving = False

                        idx = 1
                        while True:
                            if len(self.calcul_data[idx:]) < 120: # 120일치가 있는지 확인
                                print("120일치가 없음!")
                                break

                            total_price = 0
                            for value in self.calcul_data[idx: 120+idx]:
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

                if pass_success == True:
                    # 조건 포착
                    code_name = self.dynamicCall("GetMasterCodeName(QString)", code)

                    with open("files/condition_stock.txt", "a", encoding="UTF-8") as f:
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
        self.dynamicCall("SetInputValue(String, String)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(String, String)", "비밀번호", "")
        self.dynamicCall("SetInputValue(String, String)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(String, String)", "조회구분", "2")
        self.dynamicCall("CommRqData(String, String, int, String)",
                         "예수금상세현황요청", "opw00001", "0", self.screen_account_info)
        # Return: ("요청이름", "TR번호", "preNext", "화면번호")
        # EventLoop 이용해 Block
        if self.detail_account_event_loop.isRunning():
            pass
        else:
            self.detail_account_event_loop.exec_()


    def detail_account_mystock(self, sPrevNext="0"):
        print("계좌평가 잔고내역 요청")
        self.dynamicCall("SetInputValue(String, String)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(String, String)", "비밀번호", "")
        self.dynamicCall("SetInputValue(String, String)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(String, String)", "조회구분", "2")
        self.dynamicCall("CommRqData(String, String, int, String)",
                         "계좌평가잔고내역요청", "opw00018", sPrevNext, self.screen_account_info)

        if self.detail_account_event_loop.isRunning():
            pass
        else:
            self.detail_account_event_loop.exec_()


    def not_concluded_account(self, sPrevNext="0"):
        print("미체결 요청")
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "체결구분", "1")
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", "0")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "실시간미체결요청", "opt10075", sPrevNext, self.screen_account_info)
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

        self.dynamicCall("CommRqData(QString, QString, int, QString)", "주식일봉차트조회", "opt10081", sPrevNext, self.screen_calcluation_stock)
        self.calculator_event_loop.exec_()


    def read_code(self):
        if os.path.exists("files/condition_stock.txt"):
            with open("files/condition_stock.txt", "r", encoding="UTF-8") as f:
                lines = f.readlines()
                for line in lines:
                    if line != "":
                        stock_code, stock_name, stock_price = line.strip().split("\t")
                        stock_price = abs(int(stock_price))

                        self.portfolio_stock_dict.update({stock_code: {"종목명":stock_name, "현재가": stock_price}})

    def screen_number_setting(self):
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

            cnt += 1