ARG BUILD_FROM
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-pip tesseract-ocr tesseract-ocr-data-eng  && pip install vncdotool pillow pytesseract paho-mqtt
WORKDIR /opt/app
COPY app /opt/app/app
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
