FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir -r requirements.txt

COPY app/. ${LAMBDA_TASK_ROOT}/app/
COPY data/approved/. ${LAMBDA_TASK_ROOT}/data/approved/

CMD ["app.main.handler"]
