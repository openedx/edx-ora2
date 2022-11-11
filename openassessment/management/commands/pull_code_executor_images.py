"""
Command to pull docker images of different code executors.
"""
import docker

from django.core.management.base import BaseCommand

from openassessment.xblock.code_executor.config import get_all_epicbox_profiles


class Command(BaseCommand):
    """
    Pull images for all code executors.
    """

    def handle(self, *args, **options):
        client = docker.from_env()
        images = set([profile.docker_image for profile in get_all_epicbox_profiles()])

        self.stdout.write('Pulling {} images.'.format(len(images)))

        try:
            for image in images:
                self.stdout.write('Pulling {} ...\n'.format(image))
                client.images.pull(image)
        except Exception as ex:
            self.stderr.write(ex)
