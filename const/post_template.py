DEFAULT_TEMPLATE = """<b>{title_escaped}</b>
<i>{score_dotted} votes in {elapsed_smart}</i> • {thread_or_urls} ({num_comments})"""

DEFAULT_ANNOUNCEMENT_TEMPLATE = """<b>Top {resume_posts} posts of the past {resume_frequency} for</b> #{subreddit}:"""

DEFAULT_MATRIX_TEMPLATE = """**{title}**
*{score_dotted} votes in {elapsed_smart}* • [url]({url}) • [thread]({comments_url}) ({num_comments})"""
