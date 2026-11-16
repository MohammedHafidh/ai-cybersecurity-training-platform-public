# SQL injection

## Concept

SQL injection arises when application input can change the intended meaning of a SQL query. Parameterized queries help keep input separate from SQL instructions. HTTP observations alone describe requests and responses. They can leave the database outcome unknown.

## Interpreting the lab evidence

The frozen web rule flags a run with at least one SQL-like token match. It counts matches across the run. Ordinary input can include similar words and an injection attempt can lack a recognized pattern. A token match or an HTTP error cannot establish that a query changed, data was accessed, or an injection succeeded.
