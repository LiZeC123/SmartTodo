#! /bin/bash

rm -rf data/*
pytest --cov=./ --cov-report=html 