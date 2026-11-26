-- For the API.

-- The skill's state just before this answer, so a later correction to the answer
-- (he says it was a guess, or adds a reason) can redo the level change exactly.
ALTER TABLE answers ADD COLUMN skill_before jsonb;

-- An answer, the practice set and the mock test it belongs to all belong to one child.
ALTER TABLE practice_sessions ADD CONSTRAINT practice_sessions_id_child_key UNIQUE (id, child_id);
ALTER TABLE mock_tests ADD CONSTRAINT mock_tests_id_child_key UNIQUE (id, child_id);
ALTER TABLE answers ADD CONSTRAINT answers_session_same_child
    FOREIGN KEY (practice_session_id, child_id) REFERENCES practice_sessions (id, child_id);
ALTER TABLE answers ADD CONSTRAINT answers_mock_same_child
    FOREIGN KEY (mock_test_id, child_id) REFERENCES mock_tests (id, child_id) ON DELETE CASCADE;
