"""
Sample input texts for testing.
"""

# Clear factual claim
FACTUAL_INPUT = """
According to Tesla's Q4 2023 report, the company delivered approximately
1.81 million vehicles in 2023, a 38% increase year-over-year.
"""

# Opinion only
OPINION_INPUT = """
Tesla is the best car company ever. Elon Musk is a genius and the stock
is definitely going to $1000. Anyone who disagrees is wrong.
"""

# Mixed content
MIXED_INPUT = """
I think Tesla is overvalued, but they did report record deliveries of
1.81 million vehicles last year. Still, the stock price is too high.
"""

# Compound claims
COMPOUND_INPUT = """
Tesla delivered 1.81 million vehicles AND increased production by 35%
while also expanding into new markets across Asia.
"""

# Historical claim
HISTORICAL_INPUT = """
In 1969, Neil Armstrong became the first human to walk on the moon as
part of NASA's Apollo 11 mission.
"""

# Unverifiable claim
UNVERIFIABLE_INPUT = """
Sources say the company is planning a major announcement next month that
will revolutionize the industry. Multiple insiders confirm this.
"""

# Empty and edge cases
EMPTY_INPUT = ""
WHITESPACE_INPUT = "   \n\t   "
SHORT_INPUT = "Tesla."
VERY_LONG_INPUT = "Tesla " * 1000
