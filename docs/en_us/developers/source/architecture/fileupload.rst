.. _fileupload:

##########
FileUpload
##########


Overview
--------

In this document, we describe the use of the File Upload API.

By design, this is a simple API for requesting an Upload URL or Download URL
for a piece of content. The means by which the media is stored is relative to
the implementation of the File Upload Service.

This project initially has one File Upload Service implementation for
retrieving Upload / Download URLs for Amazon S3.

The URLs provided by the File Upload API are intended to be used to upload and
download content from the client to the content store directly.

In order to provide a seamless interaction on the client, this may require an
AJAX request to first retrieve the URL, then upload content. This type of
request is restricted via Cross Origin Policy, but can be resolved through CORS
configuration on the content store.

Configuration
-------------

The Amazon S3 File Upload Service requires the following settings to be
configured:

* AWS_ACCESS_KEY_ID - The AWS Access Key ID.
* AWS_SECRET_ACCESS_KEY - The associated AWS Secret Access Key.
* FILE_UPLOAD_STORAGE_BUCKET_NAME - The name of the S3 Bucket configured for uploading and downloading content.
* FILE_UPLOAD_STORAGE_PREFIX (optional) - The file prefix within the bucket for storing all content. Defaults to 'submissions_attachments'

In addition, your S3 bucket must be have CORS configuration set up to allow PUT
and GET requests to be performed across request origins.  To do so, you must:

1. Log into Amazon AWS
2. Select S3 from the available applications
3. Expand the "Permissions" section
4. Click "Edit CORS configuration"
5. Your CORS configuration must have the following values:

.. code-block:: xml

    <CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
        <CORSRule>
            <AllowedOrigin>*</AllowedOrigin>
            <AllowedHeader>*</AllowedHeader>
            <AllowedMethod>PUT</AllowedMethod>
            <AllowedMethod>GET</AllowedMethod>
        </CORSRule>
    </CORSConfiguration>

Note that you must configure an IAM user and role for access to your S3 bucket.

1. From Amazon AWS, select services, IAM.
2. Select Groups
3. Create a new 'upload' group.
4. This new group will require a policy. The following is a lenient upload
policy for S3:

.. code-block:: json

    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "Stmt1403207543000",
          "Effect": "Allow",
          "Action": [
            "s3:*"
          ],
          "Resource": [
            "*"
          ]
        }
      ]
    }

5. Create a new User, add this user to the new 'upload' Group. Choose to
generate a new access key for this user.
6. This new access key must be used in the settings described above:
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.
