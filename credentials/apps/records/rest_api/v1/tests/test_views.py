from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from credentials.apps.catalog.tests.factories import (
    CourseFactory,
    CourseRunFactory,
    OrganizationFactory,
    ProgramFactory,
)
from credentials.apps.core.tests.factories import USER_PASSWORD, UserFactory
from credentials.apps.core.tests.mixins import SiteMixin
from credentials.apps.credentials.tests.factories import (
    CourseCertificateFactory,
    ProgramCertificateFactory,
    UserCredentialFactory,
)
from credentials.apps.records.api import get_program_details
from credentials.apps.records.rest_api.v1.serializers import ProgramRecordSerializer, ProgramSerializer
from credentials.apps.records.tests.factories import ProgramCertRecordFactory
from credentials.apps.records.utils import get_user_program_data


class ProgramRecordsViewTests(SiteMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.orgs = [OrganizationFactory.create(name=name, site=self.site) for name in ["TestOrg1", "TestOrg2"]]
        self.course = CourseFactory.create(site=self.site)
        self.course_runs = CourseRunFactory.create_batch(2, course=self.course)
        self.program = ProgramFactory(
            title="TestProgram1", course_runs=self.course_runs, authoring_organizations=self.orgs, site=self.site
        )
        self.course_certs = [
            CourseCertificateFactory.create(
                course_id=course_run.key,
                site=self.site,
            )
            for course_run in self.course_runs
        ]
        self.program_cert = ProgramCertificateFactory.create(program_uuid=self.program.uuid, site=self.site)
        self.course_credential_content_type = ContentType.objects.get(
            app_label="credentials", model="coursecertificate"
        )
        self.program_credential_content_type = ContentType.objects.get(
            app_label="credentials", model="programcertificate"
        )
        self.course_user_credentials = [
            UserCredentialFactory.create(
                username=self.user.username,
                credential_content_type=self.course_credential_content_type,
                credential=course_cert,
            )
            for course_cert in self.course_certs
        ]
        self.program_user_credential = UserCredentialFactory.create(
            username=self.user.username,
            credential_content_type=self.program_credential_content_type,
            credential=self.program_cert,
        )

    def serialize_program_records(self):
        request = APIRequestFactory(SERVER_NAME=self.site.domain).get("/")
        return ProgramSerializer(
            get_user_program_data(
                self.user.username, self.site, include_empty_programs=False, include_retired_programs=True
            ),
            context={"request": request},
            many=True,
        ).data

    def serialize_program_record_details(self, is_public):
        url = "/" + str(self.program.uuid) + "/?is_public=" + str(is_public)
        request = APIRequestFactory(SERVER_NAME=self.site.domain).get(url)
        return ProgramRecordSerializer(
            get_program_details(
                request_user=self.user, request_site=self.site, uuid=self.program.uuid, is_public=is_public
            ),
            context={"request": request},
        ).data

    def test_deny_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get("/records/api/v1/program_records/")
        self.assertEqual(response.status_code, 401)

    def test_allow_authenticated_user(self):
        """Verify the endpoint requires an authenticated user."""
        self.client.logout()
        self.client.login(username=self.user.username, password=USER_PASSWORD)
        response = self.client.get("/records/api/v1/program_records/")
        self.assertEqual(response.status_code, 200)

    def test_get(self):
        self.client.login(username=self.user.username, password=USER_PASSWORD)
        response = self.client.get("/records/api/v1/program_records/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["enrolled_programs"], self.serialize_program_records())

    def test_get_private_details(self):
        self.client.login(username=self.user.username, password=USER_PASSWORD)
        uuid = str(self.program.uuid).replace("-", "")

        response = self.client.get("/records/api/v1/program_records/" + uuid + "/?is_public=false")
        self.assertEqual(response.status_code, 200)

        # Initialize two variables to hold data we intend to mutate
        response_dict = response.data
        serializer_dict = self.serialize_program_record_details(False)
        # We want to omit "last_updated" from the test as it will always be different
        del response_dict["record"]["program"]["last_updated"]
        del serializer_dict["record"]["program"]["last_updated"]
        # Remove any "-" from the uuid in the serializer
        serializer_dict["uuid"] = serializer_dict["uuid"].replace("-", "")

        self.assertEqual(response_dict, serializer_dict)
        self.assertFalse(response.data["is_public"], "Query paramater is set to public when it should be private")

    def test_get_public_details(self):
        self.client.login(username=self.user.username, password=USER_PASSWORD)
        # Create ProgramCertRecord for public request
        ProgramCertRecordFactory(uuid=self.program.uuid, program=self.program, user=self.user)
        uuid = str(self.program.uuid).replace("-", "")

        response = self.client.get("/records/api/v1/program_records/" + uuid + "/?is_public=true")
        self.assertEqual(response.status_code, 200)

        # Initialize two variables to hold data we intend to mutate
        response_dict = response.data
        serializer_dict = self.serialize_program_record_details(True)
        # We want to omit "last_updated" from the test as it will always be different
        del response_dict["record"]["program"]["last_updated"]
        del serializer_dict["record"]["program"]["last_updated"]
        # Remove any "-" from the uuid in the serializer
        serializer_dict["uuid"] = serializer_dict["uuid"].replace("-", "")

        self.assertEqual(response_dict, serializer_dict)
        self.assertTrue(response.data["is_public"], "Query paramater is set to private when it should be public")
