#!/usr/bin/env bash

echo "Stopping services..."
sudo service nginx stop || true
sudo stop workbench || true
sudo stop celery || true
sudo stop flower || true

echo "Updating ORA2..."
cd /home/vagrant/edx-ora2 && ./scripts/install.sh

echo "Updating the database..."
cd /home/vagrant/edx-ora2 && python manage.py syncdb --migrate --noinput --settings settings.vagrant

echo "Collecting static assets..."
cd /home/vagrant/edx-ora2 && python manage.py collectstatic --noinput --settings settings.vagrant

echo "Restarting services..."
sudo start workbench || true
sudo start celery || true
sudo start flower || true
sudo service nginx start || true
