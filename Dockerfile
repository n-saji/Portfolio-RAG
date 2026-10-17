FROM public.ecr.aws/lambda/python:3.12

COPY requirements.lock ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir -r requirements.lock

COPY app/. ${LAMBDA_TASK_ROOT}/app/

CMD ["app.main.handler"]
