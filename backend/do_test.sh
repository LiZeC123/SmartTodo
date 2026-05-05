#! /bin/bash

mv data/ data_bk/
pytest --cov=./ --cov-report=html 
rm -rf data/*
mv data_bk/ data/