"""
Interface for all Peer Grading Workflow. Covers all requests made for Peer Grading.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from models import Status
from common_grading.models import Essay
from serializers import StatusSerializer
from common_grading.serializers import EssaySerializer


class EssayViewSet(viewsets.ModelViewSet):

    queryset = Essay.objects.all()
    serializer_class = EssaySerializer

    def create(self, request, *args, **kwargs):
        """
        Submit an essay to be graded. This specifically requests that the given essay should be graded by peers.
        @param self: Self.
        @param request: Student, Question, and Essay information will be passed through via an HTTP Request.
        @return: Once an essay has been submitted, the student's status for beginning peer grading should be immediately
                 returned. See student_status for more information.
        """
        # TODO Copied 99% of this from Django REST mixins.py to inject 'peer' to grading_type. Figure out what I actually want...
        data = request.DATA.copy()
        data['grading_type'] = "peer"
        serializer = self.get_serializer(data=data, files=request.FILES)

        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True)
            self.post_save(self.object, created=True)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieves an essay for grading. This may be a calibration essay if the student requires calibration. If not, they
        will begin to grade actual essays for the particular question.
        @param self: Self.
        @param request: An HTTP Request with the student information, and location information, allowing the retrieval of
                        an appropriate essay to grade.
        @return: Response will contain essay grading information, or student status information regarding why an essay could
                 not be retrieved.
        """
        pass

    def get(self, request):
        """
        Notification message to determine if the submitted essay for a student is still being processed (graded) or has been
        fully graded, in which case the grade can be returned.
        @param self: Self.
        @param request: An HTTP request for the grade of a particular submission. Requires student and question information.
        @return: The requested grade, or status of the submission.
        """
        pass

    def update(self, request, *args, **kwargs):
        """
        Grading Updates from Peer Reviews.
        @param request:
        @param args:
        @param kwargs:
        @return:
        """
        pass


class StatusViewSet(viewsets.ModelViewSet):

    queryset = Status.objects.all()
    serializer_class = StatusSerializer

    def get(self, request):
        """
        Check to see if the student is ready to grade essays. In order to determine if the student can begin grading,
        the follow criteria must be met:
        1) The student has submitted an essay.
        2) The instructor has graded enough enough calibration essays.
        3) The student has graded enough calibration essays.
        4) There essays available to be graded.
        @param self: Self.
        @param request: An HTTP Request containing the student information and the location of this particular open ended
                        question.
        @return: A JSON response indicating the state of grading for this particular. The student may be given instruction
                 based on this status.
        """
        pass
