-- Rules the database enforces itself, found in an edge-case review of 0001.

-- Levels are 1 to 5; reward points 0 to 5; goals at least 1.
ALTER TABLE problems       ADD CONSTRAINT level_range  CHECK (level BETWEEN 1 AND 5);
ALTER TABLE answers        ADD CONSTRAINT level_range  CHECK (level BETWEEN 1 AND 5);
ALTER TABLE answers        ADD CONSTRAINT points_range CHECK (points BETWEEN 0 AND 5);
ALTER TABLE skill_progress ADD CONSTRAINT level_range  CHECK (level BETWEEN 1 AND 5);
ALTER TABLE children       ADD CONSTRAINT goals_positive CHECK (daily_goal > 0 AND weekly_goal > 0);

-- A multiple-choice problem has choices and a key that points at one of them;
-- a typed-answer problem has at least one accepted answer.
-- COALESCE(..., false) matters: a CHECK on a missing value would otherwise pass.
ALTER TABLE problems ADD CONSTRAINT choice_has_key CHECK (
    answer_kind <> 'choice' OR COALESCE(jsonb_typeof(choices) = 'array' AND answer_index >= 0
                                        AND answer_index < jsonb_array_length(choices), false));
ALTER TABLE problems ADD CONSTRAINT typed_has_answers CHECK (
    answer_kind <> 'typed' OR COALESCE(jsonb_typeof(accepted_answers) = 'array'
                                       AND jsonb_array_length(accepted_answers) > 0, false));

-- Only a mock test answer can point at a mock test. (Imported mock answers may have no link,
-- since the hosted app kept old test scores but not their questions.)
ALTER TABLE answers ADD CONSTRAINT mock_link CHECK (mock_test_id IS NULL OR mode = 'mock');

-- One child of a name per family (the import relies on it).
ALTER TABLE children ADD CONSTRAINT children_family_name_key UNIQUE (family_id, first_name);

-- Parent-added topics belong to a family, so the same id can exist in two families.
ALTER TABLE custom_topics DROP CONSTRAINT custom_topics_skill_id_key;
ALTER TABLE custom_topics ADD CONSTRAINT custom_topics_family_skill_key UNIQUE (family_id, skill_id);

-- Resuming needs a single answer: one open practice set and one live mock test per child.
CREATE UNIQUE INDEX practice_one_open ON practice_sessions (child_id) WHERE status = 'open';
CREATE UNIQUE INDEX mock_one_live ON mock_tests (child_id) WHERE status IN ('preparing', 'in_progress');

-- A test asks each problem once and keeps one (final) answer per problem.
ALTER TABLE mock_test_items ADD CONSTRAINT mock_items_problem_key UNIQUE (mock_test_id, problem_id);
CREATE UNIQUE INDEX answers_one_per_mock_problem ON answers (mock_test_id, problem_id) WHERE mock_test_id IS NOT NULL;

-- The test clock ends after it starts.
ALTER TABLE mock_tests ADD CONSTRAINT clock_order CHECK (ends_at IS NULL OR started_at IS NULL OR ends_at > started_at);
