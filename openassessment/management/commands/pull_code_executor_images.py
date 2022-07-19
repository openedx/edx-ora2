"""
Command to pull docker images of different code executors.
"""
import docker

from django.core.management.base import BaseCommand

from openassessment.xblock.code_executor.config import get_all_epicbox_profiles


class Command(BaseCommand):
    """
    Query aggregated open assessment data, write to .csv
    """

    def handle(self, *args, **options):
        """
        Run the command.
        """
        client = docker.from_env()
        images = set([profile.docker_image for profile in get_all_epicbox_profiles()])

        self.stdout.write('Pulling {} images.'.format(len(images)))

        try:
            for image in images:
                self.stdout.write('Pulling {} ...\n'.format(image))
                client.images.pull(image)
        except Exception as ex:
            self.stderr.write(ex)
