FROM jupyter/base-notebook
RUN pip install Flask==0.12
RUN pip install requests
RUN pip install line-bot-sdk
RUN pip install googletrans
RUN pip install pymongo


