single(a;b;c;d;"e f").

{ single(g;h) } 1.

double(d(S1, S2)) :- single(S1), single(S2).

triple(fixed, D1, D2) :- double(D1), double(D2).

nested(
  nested(
    one,
    nested(
      three,
      four
    )
  ),
  five,
  nested(
    six,
    seven
  )
).

contains_spaces("This string contains spaces.").
contains_parens("This one has (parentheses)).").
contains_quotes("This one \"even\" has quotes \".").
