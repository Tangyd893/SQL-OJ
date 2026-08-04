CREATE TABLE courses (
  course_id INTEGER PRIMARY KEY,
  title TEXT NOT NULL
);

CREATE TABLE enrollments (
  student_id INTEGER NOT NULL,
  course_id INTEGER NOT NULL
);

INSERT INTO courses (course_id, title) VALUES
  (101, 'Database'),
  (102, 'Algorithms'),
  (103, 'Networks');

INSERT INTO enrollments (student_id, course_id) VALUES
  (1, 101), (2, 101), (3, 101),
  (1, 102), (2, 102),
  (4, 103);
