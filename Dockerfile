FROM python:2

# Update packages
RUN apt-get update -y

RUN mkdir ./src

# Bundle app source
COPY . /src

# Add test version of actingweb library
#RUN pip install --index-url https://test.pypi.org/simple/ actingweb
RUN pip install -r ./src/requirements.txt

# Expose
EXPOSE 5000

# Run
CMD ["python", "/src/application.py"]