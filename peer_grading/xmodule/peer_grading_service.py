import logging

log = logging.getLogger(__name__)

class PeerGradingService(object):
    """
    Interface with the grading controller for peer grading
    TODO: Create service communication with views. ?
    """
    def __init__(self, config, system):
        config['system'] = system
        self.url = config['url'] + config['peer_grading']
        self.login_url = self.url + '/login/'
        self.submit_peer_essay = self.url + '/submit_peer_essay/'
        self.request_grade = self.url + '/request_grade/'
        self.grade_essay = self.url + '/grade_essay/'
        self.student_status = self.url + '/student_status/'
        self.system = system
