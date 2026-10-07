import datetime

from addict import Dict
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from admissions.consts import AdmissionStatus, ApplicantStatus, Priority
from admissions.models import (
    Admission,
    AdmissionAvailableInternalGroupPositionData,
    Applicant,
    ApplicantRecommendation,
    InternalGroupPositionPriority,
    Interview,
    InterviewLocation,
)
from ksg_nett.schema import schema
from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    InternalGroupPositionMembership,
)
from users.models import User

INTERNAL_GROUP_APPLICANTS_DATA_QUERY = """
    query InternalGroupApplicantsDataQuery($internalGroup: ID!) {
      internalGroupApplicantsData(internalGroup: $internalGroup) {
        firstPriorities { ...ApplicantFields }
        secondPriorities { ...ApplicantFields }
        thirdPriorities { ...ApplicantFields }
      }
    }
    fragment ApplicantFields on ApplicantNode {
      id
      fullName
      priorities { id internalGroupPosition { id name } }
      interviewerFromInternalGroup(internalGroupId: $internalGroup)
      interviewIsCovered(internalGroupId: $internalGroup)
      iAmAttendingInterview
      interview { id interviewers { id initials getFullWithNickName } }
    }
"""

PRIORITY_FIELDS = """
    id
    internalGroupPriority
    applicantPriority
    applicant { id fullName interview { id interviewers { id fullName } } }
    internalGroupPosition { internalGroup { id name } }
"""

INTERNAL_GROUP_DISCUSSION_DATA_QUERY = f"""
    query InternalGroupDiscussionDataQuery($internalGroupId: ID!, $orderingKey: String) {{
      internalGroupDiscussionData(
        internalGroupId: $internalGroupId
        orderingKey: $orderingKey
      ) {{
        applicantsOpenForOtherPositions {{
          id
          priorities {{ {PRIORITY_FIELDS} }}
          internalGroupInterests {{ id internalGroup {{ id name }} }}
        }}
        applicantRecommendations {{
          id
          recommendedBy {{ id fullName }}
          applicant {{
            id
            priorities {{ {PRIORITY_FIELDS} }}
            internalGroupInterests {{ id internalGroup {{ id name }} }}
          }}
        }}
        applicants {{
          id
          priorities {{ {PRIORITY_FIELDS} }}
        }}
      }}
    }}
"""


class AdmissionsListQueryTestCase(TestCase):
    """
    Builds an admission in session with internal groups, interviewers and a helper to add
    applicants who have finished their interview.
    """

    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.admission = Admission.objects.create(
            status=AdmissionStatus.IN_SESSION, date=datetime.date.today()
        )
        self.internal_groups = []
        self.positions = []
        for index in range(3):
            internal_group = InternalGroup.objects.create(
                name=f"Group {index}", type=InternalGroup.Type.INTERNAL_GROUP
            )
            position = InternalGroupPosition.objects.create(
                name=f"Position {index}", internal_group=internal_group
            )
            AdmissionAvailableInternalGroupPositionData.objects.create(
                admission=self.admission,
                internal_group_position=position,
                available_positions=10,
            )
            self.internal_groups.append(internal_group)
            self.positions.append(position)

        self.internal_group = self.internal_groups[0]
        self.internal_group_id = to_global_id(
            "InternalGroupNode", self.internal_group.id
        )
        # One active interviewer per group, plus one whose membership in group 0 has ended
        self.interviewers = [
            self.create_member(f"interviewer{index}", self.positions[index])
            for index in range(3)
        ]
        self.former_member = self.create_member(
            "former", self.positions[0], date_ended=datetime.date(2021, 1, 1)
        )
        self.me = User.objects.create(
            username="admin", email="admin@example.com", is_superuser=True
        )
        self.location = InterviewLocation.objects.create(name="Bodegaen")
        self.interview_start = timezone.now() + timezone.timedelta(days=1)
        self.applicant_count = 0

    def create_member(self, username, position, date_ended=None):
        user = User.objects.create(
            username=username,
            email=f"{username}@example.com",
            first_name=username,
            last_name="Member",
        )
        InternalGroupPositionMembership.objects.create(
            user=user,
            position=position,
            date_joined=datetime.date(2020, 1, 1),
            date_ended=date_ended,
        )
        return user

    def create_applicant(self, positions, interviewers, **kwargs):
        index = self.applicant_count
        self.applicant_count += 1
        start = self.interview_start + timezone.timedelta(hours=index)
        interview = Interview(
            interview_start=start,
            interview_end=start + timezone.timedelta(minutes=45),
            location=self.location,
        )
        interview.save()
        interview.interviewers.add(*interviewers)
        applicant = Applicant.objects.create(
            admission=self.admission,
            first_name=f"Applicant{index}",
            last_name="Test",
            email=f"applicant{index}@example.com",
            token=f"token{index}",
            status=ApplicantStatus.INTERVIEW_FINISHED,
            interview=interview,
            **kwargs,
        )
        for position, priority in zip(
            positions, [Priority.FIRST, Priority.SECOND, Priority.THIRD]
        ):
            InternalGroupPositionPriority.objects.create(
                applicant=applicant,
                internal_group_position=position,
                applicant_priority=priority,
            )
        return applicant

    def create_typical_applicant(self):
        applicant = self.create_applicant(
            self.positions,
            [self.interviewers[0], self.interviewers[1]],
            open_for_other_positions=True,
        )
        ApplicantRecommendation.objects.create(
            recommended_by=self.interviewers[0],
            applicant=applicant,
            reasoning="Good fit",
            internal_group=self.internal_group,
        )
        return applicant

    def execute(self, query, variables):
        with CaptureQueriesContext(connection) as queries:
            result = Dict(
                self.graphql_client.execute(
                    query, variables=variables, context=Dict(user=self.me)
                )
            )
        self.assertFalse(result.errors, result.errors)
        return result.data, len(queries)

    def assert_query_count_does_not_grow(self, query, variables):
        for _ in range(3):
            self.create_typical_applicant()
        _, few_applicants = self.execute(query, variables)

        for _ in range(12):
            self.create_typical_applicant()
        _, many_applicants = self.execute(query, variables)

        self.assertEqual(few_applicants, many_applicants)


class TestInternalGroupApplicantsDataQuery(AdmissionsListQueryTestCase):
    def query(self):
        data, _ = self.execute(
            INTERNAL_GROUP_APPLICANTS_DATA_QUERY,
            {"internalGroup": self.internal_group_id},
        )
        applicants = data.internalGroupApplicantsData
        return {
            applicant.id: applicant
            for applicant in applicants.firstPriorities
            + applicants.secondPriorities
            + applicants.thirdPriorities
        }

    def test__more_applicants__same_query_count(self):
        self.assert_query_count_does_not_grow(
            INTERNAL_GROUP_APPLICANTS_DATA_QUERY,
            {"internalGroup": self.internal_group_id},
        )

    def test__interviewer_from_internal_group__interview_is_covered(self):
        applicant = self.create_applicant(
            self.positions, [self.interviewers[0], self.interviewers[1]]
        )
        result = self.query()[to_global_id("ApplicantNode", applicant.id)]
        self.assertTrue(result.interviewIsCovered)
        self.assertEqual(
            result.interviewerFromInternalGroup,
            to_global_id("UserNode", self.interviewers[0].id),
        )

    def test__only_other_and_former_members__interview_is_not_covered(self):
        applicant = self.create_applicant(
            self.positions, [self.interviewers[1], self.former_member]
        )
        result = self.query()[to_global_id("ApplicantNode", applicant.id)]
        self.assertFalse(result.interviewIsCovered)
        self.assertIsNone(result.interviewerFromInternalGroup)

    def test__one_priority_and_one_interviewer__interview_is_not_covered(self):
        applicant = self.create_applicant(self.positions[:1], [self.interviewers[0]])
        result = self.query()[to_global_id("ApplicantNode", applicant.id)]
        self.assertFalse(result.interviewIsCovered)
        self.assertEqual(
            result.interviewerFromInternalGroup,
            to_global_id("UserNode", self.interviewers[0].id),
        )

    def test__i_am_attending_interview(self):
        attending = self.create_applicant(self.positions, [self.me])
        not_attending = self.create_applicant(self.positions, [self.interviewers[0]])
        results = self.query()
        self.assertTrue(
            results[to_global_id("ApplicantNode", attending.id)].iAmAttendingInterview
        )
        self.assertFalse(
            results[
                to_global_id("ApplicantNode", not_attending.id)
            ].iAmAttendingInterview
        )

    def test__priorities__ordered_with_missing_priority_as_null(self):
        applicant = self.create_applicant(self.positions[:2], [self.interviewers[0]])
        result = self.query()[to_global_id("ApplicantNode", applicant.id)]
        self.assertEqual(
            [
                priority.internalGroupPosition.name if priority else None
                for priority in result.priorities
            ],
            ["Position 0", "Position 1", None],
        )

    def test__single_applicant_node__resolves_without_prefetch(self):
        applicant = self.create_applicant(
            self.positions, [self.interviewers[0], self.interviewers[1]]
        )
        data, _ = self.execute(
            """
            query ($id: ID!, $internalGroup: ID!) {
              applicant(id: $id) {
                interviewIsCovered(internalGroupId: $internalGroup)
                interviewerFromInternalGroup(internalGroupId: $internalGroup)
              }
            }
            """,
            {
                "id": to_global_id("ApplicantNode", applicant.id),
                "internalGroup": self.internal_group_id,
            },
        )
        self.assertTrue(data.applicant.interviewIsCovered)
        self.assertEqual(
            data.applicant.interviewerFromInternalGroup,
            to_global_id("UserNode", self.interviewers[0].id),
        )


class TestInternalGroupDiscussionDataQuery(AdmissionsListQueryTestCase):
    def test__more_applicants__same_query_count(self):
        for ordering_key in ["priorities", "interview_time"]:
            with self.subTest(ordering_key=ordering_key):
                self.assert_query_count_does_not_grow(
                    INTERNAL_GROUP_DISCUSSION_DATA_QUERY,
                    {
                        "internalGroupId": self.internal_group_id,
                        "orderingKey": ordering_key,
                    },
                )

    def test__returns_applicants_and_recommendations(self):
        applicant = self.create_typical_applicant()
        data, _ = self.execute(
            INTERNAL_GROUP_DISCUSSION_DATA_QUERY,
            {"internalGroupId": self.internal_group_id, "orderingKey": "priorities"},
        )
        discussion_data = data.internalGroupDiscussionData
        applicant_id = to_global_id("ApplicantNode", applicant.id)
        self.assertEqual([a.id for a in discussion_data.applicants], [applicant_id])
        self.assertEqual(
            [r.applicant.id for r in discussion_data.applicantRecommendations],
            [applicant_id],
        )
        self.assertEqual(
            [
                p.internalGroupPosition.internalGroup.name
                for p in discussion_data.applicants[0].priorities
            ],
            ["Group 0", "Group 1", "Group 2"],
        )


# Same selection as CURRENT_APPLICANTS_QUERY in the frontend applicants overview
CURRENT_APPLICANTS_QUERY = """
    query CurrentApplicantsQuery {
      currentApplicants {
        id
        fullName
        email
        status
        phone
        priorities {
          id
          internalGroupPosition {
            name
            id
          }
        }
      }
    }
"""


class TestCurrentApplicantsQuery(AdmissionsListQueryTestCase):
    def test__more_applicants__same_query_count(self):
        self.assert_query_count_does_not_grow(CURRENT_APPLICANTS_QUERY, {})

    def test__returns_priorities_in_order(self):
        self.create_applicant(self.positions[:2], [])
        data, _ = self.execute(CURRENT_APPLICANTS_QUERY, {})
        names = [
            priority and priority.internalGroupPosition.name
            for priority in data.currentApplicants[0].priorities
        ]
        self.assertEqual(names, ["Position 0", "Position 1", None])


class TestMissingApplicant(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)

    def execute(self, query, variables, user):
        executed = self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user)
        )
        self.assertNotIn("errors", executed)
        return Dict(executed["data"])

    def test__unknown_applicant_id__resolves_to_null(self):
        from users.tests.factories import UserWithPermissionsFactory

        user = UserWithPermissionsFactory.create(
            permissions="admissions.view_applicant"
        )
        data = self.execute(
            "query ($id: ID!) { applicant(id: $id) { id } }",
            {"id": to_global_id("ApplicantNode", 999999)},
            user,
        )
        self.assertIsNone(data.applicant)

    def test__unknown_token__resolves_to_null(self):
        from django.contrib.auth.models import AnonymousUser

        data = self.execute(
            "query ($token: String!) { getApplicantFromToken(token: $token) { id } }",
            {"token": "no-such-token"},
            AnonymousUser(),
        )
        self.assertIsNone(data.getApplicantFromToken)
