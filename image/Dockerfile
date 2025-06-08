FROM public.ecr.aws/lambda/python:3.11

# 2 - Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# 3 - Install all the packages
RUN pip install -r requirements.txt

# 4 - Copy all files in ./src to the LAMBDA_TASK_ROOT
COPY src/ ${LAMBDA_TASK_ROOT}

# 5 - Set the CMD to the handler.
CMD [ "main.handler" ]
