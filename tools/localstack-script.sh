#!/bin/bash

awslocal s3api \
    create-bucket --bucket webtext2sql-bucket \
    --create-bucket-configuration LocationConstraint=eu-central-1 \
    --region eu-central-1
echo '{"CORSRules":[{"AllowedHeaders":["*"],"AllowedMethods":["GET","POST","PUT"],"AllowedOrigins":["*"],"ExposeHeaders":["ETag"]}]}' > cors.json
awslocal s3api put-bucket-cors --bucket webtext2sql-bucket --cors-configuration file://cors.json
