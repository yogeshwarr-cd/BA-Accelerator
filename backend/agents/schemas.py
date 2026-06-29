from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Agent 1 (Requirement Intelligence) Schemas ---

class ExtractedRequirement(BaseModel):
    id: str = Field(..., description="Unique shorthand ID, e.g. REQ-001")
    content: str = Field(..., description="The clear requirement statement")
    actors: List[str] = Field(default_factory=list, description="Actors involved in this requirement")
    business_rules: List[str] = Field(default_factory=list, description="Associated business logic constraints")

class RequirementIntelligenceOutput(BaseModel):
    requirements: List[ExtractedRequirement] = Field(..., description="List of extracted system requirements")
    actors: List[str] = Field(default_factory=list, description="Global actors identified in the document")
    business_rules: List[str] = Field(default_factory=list, description="General business rules identified")
    ambiguities: List[str] = Field(default_factory=list, description="Unclear statements needing clarification")
    conflicts: List[str] = Field(default_factory=list, description="Contradicting elements identified within requirements")
    confidence_score: float = Field(..., description="Quality/completeness confidence score (0.0 to 1.0)")


# --- Agent 1 (NEW: Requirement Intelligence v2) Schemas ---

class FunctionalRequirement(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., FR-001")
    name: str = Field(..., description="Requirement name")
    description: str = Field(..., description="Clear requirement statement")
    source_text: str = Field(..., description="Exact quote from original requirement text")
    traceability_id: str = Field(..., description="fingerprint#offset for traceability")

class NonFunctionalRequirement(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., NFR-001")
    category: str = Field(..., description="Category: Performance, Security, Reliability, Availability, Maintainability, Scalability, Compliance, Accessibility, Portability, Usability")
    name: str = Field(..., description="NFR name")
    description: str = Field(..., description="Clear requirement statement")
    source_text: str = Field(..., description="Exact quote from original requirement text")
    traceability_id: str = Field(..., description="fingerprint#offset for traceability")

class BusinessRule(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., BR-001")
    type: str = Field(..., description="Rule type: Validation, Policy, Constraint, Permission, Threshold, Calculation, State Transition")
    rule: str = Field(..., description="Concise rule statement")
    description: str = Field(..., description="Detailed description")
    source_text: str = Field(..., description="Exact quote from original requirement text")
    traceability_id: str = Field(..., description="fingerprint#offset for traceability")

class Actor(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., ACT-001")
    name: str = Field(..., description="Actor name")
    type: str = Field(..., description="Type: Human, System, External API")
    description: str = Field(..., description="Actor description and responsibilities")

class Dependency(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., DEP-001")
    source: str = Field(..., description="Source requirement ID")
    target: str = Field(..., description="Target requirement ID")
    type: str = Field(..., description="Type: Blocking, Sequential, Parallel")
    description: str = Field(..., description="Dependency relationship description")

class Conflict(BaseModel):
    requirement: str = Field(..., description="Conflicting requirement ID or name")
    issue: str = Field(..., description="Description of the conflict")

class Ambiguity(BaseModel):
    requirement: str = Field(..., description="Requirement ID with ambiguity")
    term: str = Field(..., description="Ambiguous term")
    issue: str = Field(..., description="Why it's ambiguous and recommended clarification")

class MissingRequirement(BaseModel):
    area: str = Field(..., description="Missing requirement area")
    description: str = Field(..., description="Description of what's missing")

class RetryMetadata(BaseModel):
    attempts: int = Field(..., description="Number of attempts made")
    max_attempts: int = Field(..., description="Maximum attempts allowed")
    target_confidence: int = Field(..., description="Target confidence score")
    status: str = Field(..., description="Status: SUCCESS, RETRIED, MAX_RETRIES_REACHED")
    recommendation: str = Field(..., description="Recommendation for next steps")

class ValidationContext(BaseModel):
    conflicts: List[Conflict] = Field(default_factory=list, description="Detected conflicts")
    ambiguities: List[Ambiguity] = Field(default_factory=list, description="Detected ambiguities")
    missing_requirements: List[MissingRequirement] = Field(default_factory=list, description="Missing important requirements")
    domain: str = Field(..., description="Business domain classification")
    confidence_score: int = Field(..., description="Overall confidence score (0-100)")
    retry_metadata: RetryMetadata = Field(..., description="Retry attempt metadata")

class PrimaryInput(BaseModel):
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list, description="Extracted functional requirements")
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list, description="Extracted non-functional requirements")
    business_rules: List[BusinessRule] = Field(default_factory=list, description="Extracted business rules")
    actors: List[Actor] = Field(default_factory=list, description="Identified actors and stakeholders")
    dependencies: List[Dependency] = Field(default_factory=list, description="Requirement dependencies")

class Agent1RequirementIntelligenceOutput(BaseModel):
    """Agent 1 output conforming to the structured specification."""
    primary_input: PrimaryInput = Field(..., description="Extracted requirements, rules, actors, dependencies")
    validation_context: ValidationContext = Field(..., description="Quality validation, conflicts, ambiguities, domain, confidence")

    @property
    def requirements(self) -> List[ExtractedRequirement]:
        """Compatibility helper for older pipeline code expecting flat requirement items."""
        return [
            ExtractedRequirement(
                id=req.id,
                content=req.description,
                actors=[actor.name for actor in self.primary_input.actors],
                business_rules=[rule.rule for rule in self.primary_input.business_rules],
            )
            for req in self.primary_input.functional_requirements
        ]

    @property
    def actors(self) -> List[str]:
        return [actor.name for actor in self.primary_input.actors]

    @property
    def business_rules(self) -> List[str]:
        return [rule.rule for rule in self.primary_input.business_rules]

    @property
    def ambiguities(self) -> List[str]:
        return [ambiguity.issue for ambiguity in self.validation_context.ambiguities]

    @property
    def conflicts(self) -> List[str]:
        return [conflict.issue for conflict in self.validation_context.conflicts]

    @property
    def confidence_score(self) -> float:
        return float(self.validation_context.confidence_score)


# --- Agent 2 (Epic & Feature Planner) Schemas ---

class EpicPlan(BaseModel):
    id: str = Field(..., description="Epic ID, e.g., EPIC-1")
    name: str = Field(..., description="Descriptive high-level epic title")
    description: str = Field(..., description="Detailed description of the epic scope")

class FeaturePlan(BaseModel):
    id: str = Field(..., description="Feature ID, e.g., FEAT-1")
    epic_id: str = Field(..., description="Associated Epic ID")
    name: str = Field(..., description="Feature title")
    description: str = Field(..., description="Feature summary details")

class TraceMapping(BaseModel):
    requirement_id: str = Field(..., description="Shorthand requirement ID, e.g. REQ-001")
    feature_id: str = Field(..., description="Target feature identifier mapping, e.g. FEAT-1")

class EpicFeaturePlannerOutput(BaseModel):
    epics: List[EpicPlan] = Field(..., description="List of proposed epics")
    features: List[FeaturePlan] = Field(..., description="List of features grouped under epics")
    hierarchy: List[TraceMapping] = Field(..., description="Traceability list mapping requirements to features")

# --- Agent 3 (User Story Generator) Schemas ---

class AcceptanceCriteria(BaseModel):
    scenario: str = Field(..., description="Scenario description")
    given: str = Field(..., description="Preconditions")
    when: str = Field(..., description="Trigger actions")
    then: str = Field(..., description="Expected postconditions")

class UserStory(BaseModel):
    id: str = Field(..., description="Story ID, e.g., STORY-1")
    epic_id: str = Field(..., description="Parent epic reference ID")
    feature_id: str = Field(..., description="Parent feature reference ID")
    title: str = Field(..., description="Functional title of user story")
    user_story_text: str = Field(..., description="As a... I want to... So that... standard template")
    acceptance_criteria: List[AcceptanceCriteria] = Field(default_factory=list, description="Acceptance criteria list")
    trace_mappings: List[str] = Field(..., description="Reference requirement IDs, e.g., ['REQ-001']")

class UserStoryGeneratorOutput(BaseModel):
    user_stories: List[UserStory] = Field(..., description="Generated Agile user stories list")
    plain_text_summary: str = Field(..., description="Narrative summary highlighting structural updates")

# INTEGRATION NOTE
# All pipeline agents serialize their results into these Pydantic models.
# Keep schema names and attributes stable across updates to avoid breaking LangGraph state parsing.
