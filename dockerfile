FROM public.ecr.aws/lambda/python:3.9.1

RUN pip install --upgrade pip

COPY base.py ${LAMBDA_TASK_ROOT}

CMD ["base.lambda_handler"]