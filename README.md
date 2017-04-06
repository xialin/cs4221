# CS4221 Term Project
ER Diagram (XML) to JSON Schema converter

### Feature Summary
- Allow user to upload an XML file representing Entity-Relationship diagrams 
and generates JSON Schema accordingly.
- Validate uploaded file is of supported extension (.xml).
- Validate the file contains valid ER objects, e.g. no missing primary key or circular dependency etc.
- Allow user to choose primary key if multiple candidate keys are found.
- Add Unique constraints for non-primary keys.
- Allow user to merge a relationship into an entity table if [1,1] cardinality is found.
- Support weak entity.

### Project Structure
```
- hello # root dir
    - urls.py       # URL to view mapper
    - views.py      # UI logic
    - converter.py  # main convert logic
    - /data         # contains sample data for demo and test
    - /static
        - /hello    # UI assets
    - /templates
        - base.html                     # main page (container)
        - choose_key.html               # UI component for choosing primary key
        - choose_merge.html             # UI component for choosing to merge table
        - display_uploaded_file.html    # UI component for display ER diagram xml
        - upload.html                   # UI component for uploading file 
```

### How to run

#### Prerequisite
This project is built upon [Bitnami Django](https://bitnami.com/stack/django).
Make sure you set up local environment via Bitnami Django Installer.

#### Start server
Assuming you have set up the local environment with Apache server and Postgres,
you need start localhost before running the application. Bitnami provides an application to do so via GUI.

#### Start the app
To start the app, go to djangostack directory (e.g. /Applications/djangostack-1.10.6-0 on Mac).
Open use_djangostack terminal and go to the same directory via command line.
> cd /Applications/djangostack-1.10.6-0/apps/django/django_projects/cs4221

In /cs4221 directory, run the following command:
> ./manage.py runserver localhost:8888

We choose port 8888 to avoid conflict with default.

Now open your browser and enter `http://localhost:8888/hello/upload`, you will see the upload page.
You can then play with it.
