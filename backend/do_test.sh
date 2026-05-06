#! /bin/bash

mv data/ data_bk/
mkdir data/
pytest --cov=./ --cov-report=html 
rm -rf data/*
mv data_bk/ data/