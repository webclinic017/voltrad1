cd /tmp
export PYTHONPATH=/home/david/python/voltrad1
DATE=`date +%d-%m-%y` 
nohup /home/david/anaconda2/bin/python /home/david/python/voltrad1/volquotes/ib_option_chains_reader.py >> /var/log/voltrad1/ib_chain_opt_${DATE}.log 2>&1 &
