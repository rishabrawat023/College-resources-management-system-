-- ============================================================
-- Campus Resource Optimizer - database/schema.sql
-- Run this whole file in MySQL Workbench (lightning bolt button).
-- WARNING: it drops and re-creates both tables, so running it
-- again resets all data back to the sample data below.
-- ============================================================

CREATE DATABASE IF NOT EXISTS campus_optimizer;
USE campus_optimizer;

-- Drop old tables (bookings first, because it depends on resources)
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS resources;

-- ------------------------------------------------------------
-- Table 1: resources (classrooms, labs, halls, ...)
-- ------------------------------------------------------------
CREATE TABLE resources (
    resource_id   INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(50)  NOT NULL UNIQUE,   -- e.g. A-101
    resource_type VARCHAR(30)  NOT NULL,          -- Classroom, Computer Lab, Seminar Hall, Auditorium
    capacity      INT          NOT NULL,          -- number of students
    building      VARCHAR(60)  NOT NULL,
    floor         INT          NOT NULL DEFAULT 0,
    equipment     VARCHAR(200),                   -- e.g. Projector, AC
    status        VARCHAR(20)  NOT NULL DEFAULT 'Available'  -- Available or Maintenance
);

-- ------------------------------------------------------------
-- Table 2: bookings (linked to resources by a foreign key)
-- ------------------------------------------------------------
CREATE TABLE bookings (
    booking_id    INT AUTO_INCREMENT PRIMARY KEY,
    resource_id   INT          NOT NULL,
    date          DATE         NOT NULL,
    start_time    TIME         NOT NULL,
    end_time      TIME         NOT NULL,
    student_count INT          NOT NULL,
    purpose       VARCHAR(200) NOT NULL,
    status        VARCHAR(20)  NOT NULL DEFAULT 'Confirmed',  -- Confirmed or Cancelled
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id)
        ON DELETE CASCADE   -- deleting a resource also deletes its bookings
);

-- ------------------------------------------------------------
-- Sample resources
-- ------------------------------------------------------------
INSERT INTO resources (resource_id, name, resource_type, capacity, building, floor, equipment, status) VALUES
(1,  'A-101',  'Classroom',    60,  'Academic Block', 1, 'Projector, AC',                     'Available'),
(2,  'A-102',  'Classroom',    50,  'Academic Block', 1, 'Projector',                         'Available'),
(3,  'A-103',  'Classroom',    40,  'Academic Block', 1, 'Whiteboard',                        'Available'),
(4,  'A-104',  'Classroom',    45,  'Academic Block', 1, 'Projector, AC',                     'Maintenance'),
(5,  'A-105',  'Classroom',    55,  'Academic Block', 2, 'Projector, AC',                     'Available'),
(6,  'LAB-01', 'Computer Lab', 40,  'Computer Block', 1, '40 Computers, AC',                  'Available'),
(7,  'LAB-02', 'Computer Lab', 30,  'Computer Block', 2, '30 Computers',                      'Available'),
(8,  'SH-01',  'Seminar Hall', 150, 'Main Block',     1, 'Projector, Sound System, AC',       'Available'),
(9,  'SH-02',  'Seminar Hall', 100, 'Main Block',     2, 'Projector, Sound System',           'Available'),
(10, 'AUD-01', 'Auditorium',   500, 'Main Block',     0, 'Projector, Sound System, AC, Stage','Available');

-- ------------------------------------------------------------
-- Sample bookings
-- Dates use CURDATE() so the samples are always "today" or "tomorrow".
-- Try this to test conflict detection:
--   Book A-101 today from 10:30 to 11:30  ->  conflict with the first booking.
-- ------------------------------------------------------------
INSERT INTO bookings (resource_id, date, start_time, end_time, student_count, purpose, status) VALUES
(1, CURDATE(),                          '10:00:00', '11:00:00', 55, 'Data Structures lecture',   'Confirmed'),
(2, CURDATE(),                          '14:00:00', '15:00:00', 45, 'Mathematics tutorial',      'Confirmed'),
(6, CURDATE(),                          '11:00:00', '13:00:00', 38, 'Python lab practical',      'Confirmed'),
(1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00:00', '10:30:00', 50, 'Database Systems lecture', 'Confirmed'),
(8, DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00:00', '12:00:00', 120, 'Guest lecture on AI',     'Confirmed'),
(5, DATE_ADD(CURDATE(), INTERVAL 2 DAY), '13:00:00', '14:00:00', 52, 'Project review meeting',   'Confirmed');
