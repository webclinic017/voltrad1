# coding: utf-8

#27-nov-2016 Fix error:
#  ValueError: Trying to store a value with len [XX] in [CallOI??] column but
#  this column has a limit of [XXX]!

import glob
import fnmatch
import os
import sys
import config as config
import pandas as pd
import datetime as dt
import numpy as np

path = 'C:/Users/David/Dropbox/proyectos/data/'
# path = '/home/david/data/'

def run():
    os.chdir(path)
    optchain_orig = 'optchain_ib_hist_db.h5'
    pattern_optchain = 'optchain_ib_hist_db.h5*'
    optchain_out = 'optchain_ib_hist_db_new.h5'
    lst1 = glob.glob(pattern_optchain)
    lst1.remove(optchain_orig)
    print lst1
    dataframe = pd.DataFrame()
    for x in lst1:
        store_in1 = pd.HDFStore(path + x)
        root1 = store_in1.root
        print root1._v_pathname
        for lvl1 in root1:
            print lvl1._v_pathname
            if lvl1:
                df1 = store_in1.select(lvl1._v_pathname)
                dataframe = dataframe.append(df1)
                print "store_in1", len(df1), x
        store_in1.close()

    store_in1 = pd.HDFStore(path + optchain_orig)
    store_out = pd.HDFStore(path + optchain_out)
    root1 = store_in1.root
    print root1._v_pathname
    for lvl1 in root1:
        print lvl1._v_pathname
        if lvl1:
            df1 = store_in1.select(lvl1._v_pathname)
            dataframe = dataframe.append(df1)
            print "store_in1", len(df1), optchain_orig
    store_in1.close()

    dataframe.sort_index(inplace=True,ascending=[True])
    names = dataframe['symbol'].unique().tolist()
    for name in names:
        print ("Storing " + name + " in ABT ..." + str(len(dataframe)))
        joe = dataframe[dataframe.symbol == name]
        joe=joe.sort_values(by=['symbol', 'current_datetime', 'expiry', 'strike', 'right'])
        store_out.append("/" + name, joe, data_columns=True,min_itemsize={'comboLegsDescrip': 25})
    store_out.close()

if __name__ == "__main__":
    run()

