DEFAULT_TEMPLATE_2 = """<b>{title_escaped}</b>
<i>{score_dotted} votes in {elapsed_smart}</i> • {thread_or_urls} ({num_comments})"""

DEFAULT_TEMPLATE_1 = """<b>{title_escaped}</b>
{score_dotted} votes ({upvote_perc}%) in {elapsed_smart} • {num_comments} comments

{shortlink}"""

DEFAULT_TEMPLATE_3 = """<b>{title_escaped}</b>
<i>{score_dotted} votes ({upvote_perc}%) in {elapsed_smart} • {num_comments} comments</i>
{url}

{shortlink}"""

DEFAULT_TEMPLATE_4 = """{hidden_url}<b>{title_escaped}</b>
{score_dotted} votes ({upvote_perc}%) in {elapsed_smart} • {num_comments} comments

{shortlink}"""

DEFAULT_TEMPLATE_5 = """<b>{title_escaped}</b>
{score_dotted} votes ({upvote_perc}%) in {elapsed_smart} • {num_comments} comments

{shortlink} • #{subreddit}"""

DEFAULT_TEMPLATE_6 = """{hidden_url}<b>{title_escaped}</b>
{score_dotted} votes ({upvote_perc}%) in {elapsed_smart} • {num_comments} comments

{shortlink} • #{subreddit}"""

DEFAULT_TEMPLATES = (
    DEFAULT_TEMPLATE_1,
    DEFAULT_TEMPLATE_2,
    DEFAULT_TEMPLATE_3,
    DEFAULT_TEMPLATE_4,
    DEFAULT_TEMPLATE_5,
    DEFAULT_TEMPLATE_6
)

DEFAULT_ANNOUNCEMENT_TEMPLATE = """<b>Top {resume_posts} posts of the past {resume_frequency} for</b> #{subreddit}:"""


