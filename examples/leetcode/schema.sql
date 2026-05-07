CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    tags TEXT[] NOT NULL,
    statement TEXT NOT NULL,
    code_stub TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_cases (
    id SERIAL PRIMARY KEY,
    problem_id TEXT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    input TEXT NOT NULL,
    expected TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    problem_id TEXT NOT NULL REFERENCES problems(id),
    competition_id TEXT NULL,
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    status TEXT NOT NULL,
    passed_tests INTEGER NOT NULL DEFAULT 0,
    total_tests INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_submissions_competition_status ON submissions (competition_id, status);

INSERT INTO problems (id, title, difficulty, tags, statement, code_stub) VALUES
    ('two-sum', 'Two Sum', 'easy', ARRAY['array', 'hash-table'], 'Return indices of two numbers that add to target.', 'def solve(nums, target):\n    pass'),
    ('reverse-string', 'Reverse String', 'easy', ARRAY['string'], 'Return the reversed string.', 'def solve(value):\n    pass')
ON CONFLICT DO NOTHING;

INSERT INTO test_cases (problem_id, input, expected) VALUES
    ('two-sum', '([2,7,11,15], 9)', '[0, 1]'),
    ('two-sum', '([3,2,4], 6)', '[1, 2]'),
    ('reverse-string', '(''abc'',)', '''cba'''),
    ('reverse-string', '(''system'',)', '''metsys''')
ON CONFLICT DO NOTHING;
