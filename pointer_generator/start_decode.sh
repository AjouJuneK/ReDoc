export PYTHONPATH=`pwd`
MODEL=$1
python code/decode.py $MODEL >& ../log/decode_log &

