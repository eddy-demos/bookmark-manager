from urllib.parse import urlparse

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import db

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def hostname(url: str) -> str:
    try:
        return urlparse(url).hostname or url
    except Exception:
        return url


templates.env.filters["hostname"] = hostname


@app.on_event("startup")
def startup():
    db.init_db()


def validate(url: str, title: str):
    errors = {}
    if not url or not url.strip():
        errors["url"] = "URL is required."
    elif not (url.startswith("http://") or url.startswith("https://")):
        errors["url"] = "URL must start with http:// or https://."
    if not title or not title.strip():
        errors["title"] = "Title is required."
    return errors


@app.get("/", response_class=HTMLResponse)
def index(request: Request, q: str = "", tag: str = ""):
    bookmarks = db.list_bookmarks(q=q or None, tag=tag or None)
    tags = db.list_tags()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "bookmarks": bookmarks,
            "tags": tags,
            "q": q,
            "active_tag": tag,
        },
    )


@app.get("/bookmarks", response_class=HTMLResponse)
def bookmarks_partial(request: Request, q: str = "", tag: str = ""):
    bookmarks = db.list_bookmarks(q=q or None, tag=tag or None)
    return templates.TemplateResponse(
        request,
        "partials/bookmark_list.html",
        {"bookmarks": bookmarks, "q": q, "active_tag": tag},
    )


@app.get("/bookmarks/new", response_class=HTMLResponse)
def new_form(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/form.html",
        {
            "bookmark": {
                "id": None,
                "url": "",
                "title": "",
                "description": "",
                "tags": [],
            },
            "errors": {},
            "action": "/bookmarks",
            "method": "post",
        },
    )


@app.post("/bookmarks", response_class=HTMLResponse)
def create(
    request: Request,
    url: str = Form(""),
    title: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
):
    errors = validate(url, title)
    if errors:
        return templates.TemplateResponse(
            request,
            "partials/form.html",
            {
                "bookmark": {
                    "id": None,
                    "url": url,
                    "title": title,
                    "description": description,
                    "tags": [t.strip() for t in tags.split(",") if t.strip()],
                },
                "errors": errors,
                "action": "/bookmarks",
                "method": "post",
            },
            status_code=400,
        )
    db.create_bookmark(url.strip(), title.strip(), description.strip(), tags)
    bookmarks = db.list_bookmarks()
    resp = templates.TemplateResponse(
        request,
        "partials/bookmark_list.html",
        {"bookmarks": bookmarks, "q": "", "active_tag": ""},
    )
    resp.headers["HX-Trigger"] = "bookmarks-changed"
    return resp


@app.get("/bookmarks/{bookmark_id}/edit", response_class=HTMLResponse)
def edit_form(request: Request, bookmark_id: int):
    b = db.get_bookmark(bookmark_id)
    if not b:
        return Response(status_code=404)
    return templates.TemplateResponse(
        request,
        "partials/form.html",
        {
            "bookmark": b,
            "errors": {},
            "action": f"/bookmarks/{bookmark_id}",
            "method": "put",
        },
    )


@app.put("/bookmarks/{bookmark_id}", response_class=HTMLResponse)
def update(
    request: Request,
    bookmark_id: int,
    url: str = Form(""),
    title: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
):
    errors = validate(url, title)
    if errors:
        return templates.TemplateResponse(
            request,
            "partials/form.html",
            {
                "bookmark": {
                    "id": bookmark_id,
                    "url": url,
                    "title": title,
                    "description": description,
                    "tags": [t.strip() for t in tags.split(",") if t.strip()],
                },
                "errors": errors,
                "action": f"/bookmarks/{bookmark_id}",
                "method": "put",
            },
            status_code=400,
        )
    db.update_bookmark(
        bookmark_id, url.strip(), title.strip(), description.strip(), tags
    )
    bookmarks = db.list_bookmarks()
    resp = templates.TemplateResponse(
        request,
        "partials/bookmark_list.html",
        {"bookmarks": bookmarks, "q": "", "active_tag": ""},
    )
    resp.headers["HX-Trigger"] = "bookmarks-changed"
    return resp


@app.delete("/bookmarks/{bookmark_id}")
def delete(bookmark_id: int):
    db.delete_bookmark(bookmark_id)
    resp = Response(status_code=200)
    resp.headers["HX-Trigger"] = "bookmarks-changed"
    return resp


@app.get("/tags", response_class=HTMLResponse)
def tags_partial(request: Request, tag: str = ""):
    tags = db.list_tags()
    return templates.TemplateResponse(
        request,
        "partials/tags.html",
        {"tags": tags, "active_tag": tag},
    )
