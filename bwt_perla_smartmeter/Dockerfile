ARG BUILD_FROM
FROM ${BUILD_FROM}

# python + tools + tesseract (binary + eng language data)
RUN apk add --no-cache     python3 py3-pip bash jq     tesseract-ocr tesseract-ocr-data-eng   && python3 -m pip install --no-cache-dir --upgrade pip

WORKDIR /opt/app

COPY requirements.txt /opt/app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/app/requirements.txt

COPY app /opt/app/app
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
