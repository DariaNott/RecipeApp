import re
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

templates = Jinja2Templates(directory="templates")


def filter_datetime(value):
    if value is None:
        return "Не вказано"
    try:
        return value.strftime("%d.%m.%Y %H:%M")
    except AttributeError:
        return str(value)


@pass_context
def filter_link_recipes(context, value):
    recipe_links_map = context.get('recipe_links_map', {})
    if value is None:
        return ""

    links_map = recipe_links_map or {}

    def replace_link(match):
        recipe_title = match.group(1)
        clean_title = recipe_title.lower().strip()
        recipe_id = links_map.get(clean_title)
        if recipe_id:
            return f'<a href="/recipe/{recipe_id}" class="recipe-wiki-link">{recipe_title}</a>'
        return recipe_title

    return re.sub(r'\[\[(.*?)\]\]', replace_link, str(value))


templates.env.filters["datetime"] = filter_datetime
templates.env.filters["link_recipes"] = filter_link_recipes
