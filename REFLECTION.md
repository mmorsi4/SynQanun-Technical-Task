## Issues

1. Parsing the ``law`` documents was very difficult. The styling could not be used to specify articles and so I had to depend on regular expressions a lot.
2. If the data was stored in a NoSQL database, it would be much easier to retrieve the data using text similarity instead of having to use ``ILIKE`` for every text field after joining the tables.
3. I was figuring out how to use Docker and the only command I really know is ``docker compose up --build`` 😅

## Future Improvements

1. XML traversal of the word document would've probably been easier, but I haven't tried that approach due to lack of time.
2. ``ILIKE`` is too basic, but I am unaware of lemmatization/stemming techniques to use for the Arabic language in PostgreSQL.
3. Multithreading to achieve bulk ingestion in parser.
4. Handle document de-duplication in parser not in database initialization.
5. Reduce the overall complexity of the data retrieval logic in the ``GET`` endpoint.

## What I would have changed in the task definition

I would need to change the fact that the database needs to strictly be three tables.
