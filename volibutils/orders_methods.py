import volibutils.sync_client as ib
from volsetup import config
import datetime as dt
import pandas as pd
import numpy as np
import swigibpy as sy
from volibutils.RequestOptionData import RequestOptionData
from volibutils.RequestUnderlyingData import RequestUnderlyingData
from volsetup.logger import logger
from swigibpy import Contract as IBcontract
from swigibpy import Order as IBOrder
import time

def init_func():
    globalconf = config.GlobalConfig(level=logger.ERROR)
    log = globalconf.log
    client = ib.IBClient(globalconf)
    clientid1 = int(globalconf.config['ib_api']['clientid_orders'])
    client.connect(clientid1=clientid1)

    #this is to try to fit in one line each row od a dataframe when printing to console
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)

    return client , log

def end_func(client):
    client.disconnect()

def bs_resolve(x):
    if x<0:
        return 'SELL'
    if x>0:
        return 'BUY'
    if x==0:
        raise Exception("trying to trade with zero")

def get_contract_details(symbol,conId=None):
    """
    In the future will get details fro DB given a ConId
    There will be a process that populate in background this table DB
    with all the potential contracts and the corresponding contract ID
    """
    db1={
        "ES":{"secType":"FOP","exchange":"GLOBEX","multiplier":"50","currency":"USD",
              "underlType":"FUT","underlCurrency":"XXX","underlExchange":"GLOBEX"},
        "SPY":{"secType":"OPT","exchange":"SMART","multiplier":"100","currency":"USD",
               "underlType":"STK","underlCurrency":"USD","underlExchange":"SMART"}
    }
    #if conId is None:
    return db1[symbol]

def get_order_defaults():
    db1={"tif":"GTC","transmit":True,'ratio':1}
    return db1

def place_plain_order(expiry,symbol,right,strike,orderType,quantity,lmtPrice,orderId):
    """
    Place a sinlge option order
    """
    if orderId <=0:
        orderId = None

    client, log = init_func()
    log.info("placing order ")
    ibcontract = IBcontract()
    ibcontract.secType = get_contract_details(symbol)["secType"]
    ibcontract.expiry=expiry
    ibcontract.symbol=symbol
    ibcontract.exchange=get_contract_details(symbol)["exchange"]
    ibcontract.right=right
    ibcontract.strike=strike
    ibcontract.multiplier=get_contract_details(symbol)["multiplier"]
    ibcontract.currency=get_contract_details(symbol)["currency"]

    iborder = IBOrder()
    iborder.action = bs_resolve(quantity)
    iborder.lmtPrice = lmtPrice
    iborder.orderType = orderType
    iborder.totalQuantity = abs(quantity)
    iborder.tif = get_order_defaults()["tif"]
    iborder.transmit = get_order_defaults()["transmit"]

    orderid1 = client.place_new_IB_order(ibcontract, iborder, orderid=orderId)
    print("orderid [%s] " % (str(orderid1)))
    end_func(client=client)

def place_or_modif_spread_order(expiry,symbol,right,strike_l,strike_s,orderType,quantity,lmtPrice,orderId):
    """
    Place new option spread order or modify existing order
    Put orderId <= 0 if new order
    """

    """
    Modification of an open order through the API can be achieved by the same client which placed the original order.
    In the case of orders placed manually in TWS, the order can be modified by the client with ID 0.

    To modify an order, simply call the IBApi.EClient.placeOrder function again with the same parameters used to place
    the original order, except for the changed parameter. This includes the IBApi.Order.OrderId, which must match the
    IBApi.Order.OrderId of the original. It is not generally recommended to try to change order parameters other than
    the order price and order size. To change other parameters, it might be preferable to cancel the original order
    and place a new order.
    """
    # http://interactivebrokers.github.io/tws-api/modifying_orders.html#gsc.tab=0



    if orderId <=0:
        orderId = None
    client, log = init_func()
    log.info("placing order ")
    underl = {
            1001:RequestOptionData(symbol,
                                   get_contract_details(symbol)["secType"],
                                   expiry,
                                   strike_l,
                                   right,
                                   get_contract_details(symbol)["multiplier"],
                                   get_contract_details(symbol)["exchange"],
                                   get_contract_details(symbol)["currency"],
                                   1001),
            1002: RequestOptionData(symbol,
                                    get_contract_details(symbol)["secType"],
                                    expiry,
                                    strike_s,
                                    right,
                                    get_contract_details(symbol)["multiplier"],
                                    get_contract_details(symbol)["exchange"],
                                    get_contract_details(symbol)["currency"],
                                    1002)
    }
    action1 = {1001:"BUY",1002:"SELL"}
    list_results = client.getOptionsChain(underl)
    legs = []
    log.info("Number of requests [%d]" % (len(list_results)) )
    for reqId, request in list_results.iteritems():
        log.info ("Requestid [%d]: Option[%s] Results [%d]" % ( reqId , str(request.get_in_data()), len(request.optionsChain) ))
        for opt1 in request.optionsChain:
            leg1 = sy.ComboLeg()
            leg1.conId = opt1['conId']
            leg1.ratio = get_order_defaults()["ratio"]
            leg1.action = action1[reqId]
            leg1.exchange = opt1['exchange']
            legs.append(leg1)
    #sy.Contract.comboLegs
    ibcontract = IBcontract()
    ibcontract.comboLegs = sy.ComboLegList(legs)
    ibcontract.symbol = symbol
    ibcontract.secType = "BAG"  # BAG is the security type for COMBO order
    ibcontract.exchange=get_contract_details(symbol)["exchange"]
    ibcontract.currency=get_contract_details(symbol)["currency"]
    iborder = IBOrder()
    iborder.action = bs_resolve(quantity)
    iborder.lmtPrice = lmtPrice
    iborder.orderType = orderType
    iborder.totalQuantity = abs(quantity)
    iborder.tif = get_order_defaults()["tif"]
    iborder.transmit = get_order_defaults()["transmit"]
    orderid1 = client.place_new_IB_order(ibcontract, iborder, orderid=orderId)
    print("orderid [%s] " % (str(orderid1)))
    end_func(client=client)

def list_open_orders():
    """
    List all currently open orders for this client
    """
    client, log = init_func()
    log.info("list orders ")

    order_structure = client.get_open_orders()
    df1 = pd.DataFrame()
    for idx, x in order_structure.iteritems():
        temp=pd.DataFrame.from_dict(x, orient='index').transpose()
        df1=df1.append(temp)
    if not df1.empty:
        df1=df1.set_index(['orderid'],drop=True)
    print(df1)

    end_func(client=client)

def modify_open_order(orderId):
    client, log = init_func()
    end_func(client=client)

def cancel_open_order(orderId):
    """
    Cancel open order identified with orderId
    """
    client, log = init_func()
    client.cancelOrder(orderId)
    end_func(client=client)


def cancel_all_open_orders():
    """
    Cancel all open orders
    """
    client, log = init_func()
    client.reqGlobalCancel()
    end_func(client=client)


def list_prices_before_trade(symbol,expiry,query):
    """
    List prices before trade
    """
    query1 = query.split(",")
    client, log = init_func()
    ctrt = {}
    for idx, x in enumerate(query1):
        ctrt[idx] = RequestOptionData(symbol,
                                      get_contract_details(symbol)["secType"],
                                      expiry,
                                      float(x[1:]),
                                      x[:1],
                                      get_contract_details(symbol)["multiplier"],
                                      get_contract_details(symbol)["exchange"],
                                      get_contract_details(symbol)["currency"],
                                      idx)
    log.info("[%s]" % (str(ctrt)))
    ctrt_prc = client.getMktData(ctrt)
    log.info("[%s]" % (str(ctrt_prc)))
    df1 = pd.DataFrame()
    for id, req1 in ctrt_prc.iteritems():
        subset_dic = {k: req1.get_in_data()[k] for k in ('strike', 'right', 'expiry','symbol')}
        subset_dic2 = {k: req1.get_out_data()[id][k] for k in ('bidPrice', 'bidSize', 'askPrice', 'askSize','closePrice') }
        dict1 = subset_dic.copy()
        dict1.update(subset_dic2)
        temp=pd.DataFrame.from_dict(dict1, orient='index').transpose()
        df1=df1.append(temp)
    df1 = df1.set_index(['strike','right','expiry','symbol'], drop=True)
    print(df1)
    end_func(client=client)


def list_option_chain(symbol,expiry,expiry_underlying):
    """
    List option chain before trading a TIC
    """
    client, log = init_func()
    underl = {100:RequestUnderlyingData(symbol,
                                        get_contract_details(symbol)["underlType"],
                                        expiry_underlying,
                                        0,
                                        '',
                                        '',
                                        get_contract_details(symbol)["underlExchange"],
                                        get_contract_details(symbol)["underlCurrency"],
                                        100)}
    underl_prc = client.getMktData(underl)
    df1 = pd.DataFrame.from_dict(underl_prc, orient='index')
    #df1 = df1.set_index(['secType','symbol','comboLegsDescrip'], drop=True)
    print(df1)
    end_func(client=client)

def list_spread_prices_before_trade(symbol,expiry,query):
    """
    List option spread prices before trade
    """
    query1 = query.split(",")
    client, log = init_func()
    underl = {}

    for idx, x in enumerate(query1):
        underl[idx] = RequestOptionData(symbol,
                                        get_contract_details(symbol)["secType"],
                                        expiry,
                                        float(x[1:]),
                                        x[:1],
                                        get_contract_details(symbol)["multiplier"],
                                        get_contract_details(symbol)["exchange"],
                                        get_contract_details(symbol)["currency"],
                                        idx,
                                        comboLegs=None)
    action1 = {0:"BUY",1:"SELL"}
    list_results = client.getOptionsChain(underl)
    legs = []
    log.info("Number of requests [%d]" % (len(list_results)) )
    for reqId, request in list_results.iteritems():
        log.info ("Requestid [%d]: Option[%s] Results [%d]" % ( reqId , str(request.get_in_data()), len(request.optionsChain) ))
        for opt1 in request.optionsChain:
            leg1 = sy.ComboLeg()
            leg1.conId = opt1['conId']
            leg1.ratio = get_order_defaults()["ratio"]
            leg1.action = action1[reqId]
            leg1.exchange = opt1['exchange']
            legs.append(leg1)

    ibcontract = IBcontract()
    ibcontract.comboLegs = sy.ComboLegList(legs)
    ibcontract.symbol = symbol
    ibcontract.secType = "BAG"  # BAG is the security type for COMBO order
    ibcontract.exchange=get_contract_details(symbol)["exchange"]
    ibcontract.currency=get_contract_details(symbol)["currency"]

    ctrt = {}
    ctrt[100] = RequestOptionData(symbol,
                                  get_contract_details(symbol)["secType"],
                                  expiry,
                                  float(x[1:]),
                                  x[:1],
                                  get_contract_details(symbol)["multiplier"],
                                  get_contract_details(symbol)["exchange"],
                                  get_contract_details(symbol)["currency"],
                                  100,
                                  comboLegs=None,
                                  contract=ibcontract)
    ctrt_prc = client.getMktData(ctrt)
    log.info("[%s]" % (str(ctrt_prc)))
    df1 = pd.DataFrame()
    for id, req1 in ctrt_prc.iteritems():
        subset_dic = {k: req1.get_in_data()[k] for k in ('secType','symbol','comboLegsDescrip')}
        subset_dic2 = {k: req1.get_out_data()[id][k] for k in ('bidPrice', 'bidSize', 'askPrice', 'askSize') }
        dict1 = subset_dic.copy()
        dict1.update(subset_dic2)
        temp=pd.DataFrame.from_dict(dict1, orient='index').transpose()
        df1=df1.append(temp)
    df1 = df1.set_index(['secType','symbol','comboLegsDescrip'], drop=True)
    print(df1)
    end_func(client=client)

if __name__=="__main__":
    #list_prices_before_trade(symbol="ES",expiry="20170120",query='C2300.0,C2350.0,P2100.0,P2150.0')
    #list_spread_prices_before_trade(symbol="ES",expiry="20170120",query='C2300.0,C2350.0')
    #place_plain_order(expiry="20170120",symbol="ES",right="C",strike=2200.0,orderType="LMT",quantity=2,lmtPrice=5.0)
    #place_or_modif_spread_order(expiry="20170120",symbol="ES",right="C",strike_l=2300.0,
    #                   strike_s=2350.0,orderType="LMT",quantity=-1,lmtPrice=3.7,orderId=-1)
    list_open_orders()

