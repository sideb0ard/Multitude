drop table if exists answers;
drop table if exists questions;
drop table if exists respondents;
drop table if exists surveys;

create table answers (
  id integer primary key autoincrement,
  respondent_id integer not null,
  question_id integer not null,
  text string not null
);

create table questions (
  id integer primary key autoincrement,
  survey_id integer not null,
  question_no integer not null,
  text string not null
);

create table respondents (
  id integer primary key autoincrement,
  name string not null,
  phone_no string not null
);

create table surveys (
  id integer primary key autoincrement,
  title string not null
);
