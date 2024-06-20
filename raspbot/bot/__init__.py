"""
The bot package.

This package contains all of the routes and handlers for the bot.

The main parts:
  - constants, where all the text found in the buttons and messages is stored, as well
    as the states of the bot, callbacks and callback factories;
  - routes, containing handlers and keyboards related to searching for a route between
    two points;
  - timetable, containing handlers and keyboards related to showing the actual timetable
    when the route is already determined;
  - users, containing handlers and keyboards related to the user's recent searches
    and favorites.

Bot currently uses polling.
"""
