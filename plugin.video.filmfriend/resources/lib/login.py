# -*- coding: utf-8 -*-
from urllib.parse import urljoin, urlparse, parse_qs
import requests
import xbmc
import xbmcgui
import xbmcaddon
import libmediathek4utils as lm4utils
from bs4 import BeautifulSoup

BASE_URL = "https://api.vod.filmwerte.de/api/v1/"


def pick():
    j = requests.get(
        f"{BASE_URL}tenant-groups/fba2f8b5-6a3a-4da3-b555-21613a88d3ef/tenants?orderBy=DisplayCategory&sortDirection=Ascending&skip=&take=1000"
    ).json()
    l = []
    for item in j["items"]:
        l.append(xbmcgui.ListItem(f'{item["displayCategory"]} - {item["displayName"]}'))
    i = xbmcgui.Dialog().select(lm4utils.getTranslation(30010), l)

    domain = j["items"][int(i)]["domain"]
    tenant = j["items"][int(i)]["id"]
    library = j["items"][int(i)]["displayName"]

    username = xbmcgui.Dialog().input(lm4utils.getTranslation(30500))
    if username == "":
        lm4utils.displayMsg(
            lm4utils.getTranslation(30501), lm4utils.getTranslation(30502)
        )
        return

    password = xbmcgui.Dialog().input(lm4utils.getTranslation(30503))
    if password == "":
        lm4utils.displayMsg(
            lm4utils.getTranslation(30504), lm4utils.getTranslation(30505)
        )
        return

    r = requests.get(
        f"{BASE_URL}customers(tenant)/{tenant}/identity-providers?orderBy=&sortDirection="
    )
    if r.text == "":
        lm4utils.displayMsg(
            lm4utils.getTranslation(30506), lm4utils.getTranslation(30507)
        )
        return

    j = r.json()
    provider = j["items"][0]["id"]
    client_id = f"tenant-{tenant}-filmwerte-vod-frontend"
    kind = j["items"][0]["kind"]

    if kind == "OpenId":
        # For OpenID we don't know the login form of the OpenID provider
        # Lets try some heuristic to get the input fields
        passwd_field_found = False
        lm4utils.displayMsg(
            lm4utils.getTranslation(30013), lm4utils.getTranslation(30509)
        )
        # we need a return uri
        request_session = requests.Session()
        domain_request = request_session.get(
            f"https://api.tenant.frontend.vod.filmwerte.de/v10/{tenant}"
        )
        tenant_domain = domain_request.json().get("clients").get("web").get("domain")
        # get the OpenID provider login page
        oidc_login_request = request_session.get(
            f"https://api.vod.filmwerte.de/connect/authorize-external?clientId={client_id}&provider={provider}&redirectUri=https://{tenant_domain}"
        )
        # parse the login page
        xbmc.log(f"filmfriend: oidc_login_request: {oidc_login_request.text}")
        doc = BeautifulSoup(oidc_login_request.content, "html.parser")
        # lookup all forms if there is a password input field
        for form in doc.findAll("form"):
            for input_tag in form.findAll("input"):
                if input_tag.attrs.get("type", "text").lower() == "password":
                    passwd_field_found = True
            # if we found a password field
            if passwd_field_found:
                data = {}
                for input_tag in form.findAll("input"):
                    if not (input_tag.attrs.get(
                        "type"
                    ) == "submit" and "CANC" in input_tag.attrs.get("name")):
                        if (
                            input_tag.attrs.get("type") == "hidden"
                            or input_tag.attrs.get("type") == "submit"
                        ):
                            data[input_tag.attrs.get("name")] = input_tag.attrs.get(
                                "value"
                            )
                        elif input_tag.attrs.get("type").lower() == "password":
                            data[input_tag.attrs.get("name")] = password
                        elif input_tag.attrs.get("type", "text").lower() == "text":
                            data[input_tag.attrs.get("name")] = username
                # try to login, hopping we have the right inputs
                if form.attrs.get("method") == "post":
                    res = request_session.post(
                        urljoin(oidc_login_request.url, form.attrs.get("action")),
                        data=data,
                    )
                elif form.attrs.get("method") == "get":
                    res = request_session.get(
                        urljoin(oidc_login_request.url, form.attrs.get("action")),
                        params=data,
                    )
                xbmc.log(f"filmfriend: login: {res.url} = > {res.text}")
                # check if there is a second form (like age verification or so)
                if (
                    res.ok
                    and tenant_domain not in res.url
                    and len(res.history) == 0
                    and "text/html" in res.headers.get("content-type")
                ):
                    doc2 = BeautifulSoup(res.content, "html.parser")
                    form = doc2.find("form")
                    data = {}
                    for input_tag in form.findAll("input"):
                        if input_tag.attrs.get(
                            "type"
                        ) == "submit" and "CANC" not in input_tag.attrs.get("name"):
                            data[input_tag.attrs.get("name")] = input_tag.attrs.get(
                                "value"
                            )
                    if form.attrs.get("method") == "post":
                        res = request_session.post(
                            urljoin(res.url, form.attrs.get("action")), data=data
                        )
                    elif form.attrs.get("method") == "get":
                        res = request_session.get(
                            urljoin(res.url, form.attrs.get("action")), params=data
                        )
                    xbmc.log(f"filmfriend: age verification: {res.url} = > {res.text}")
                # check if we have an access_token
                if res.ok and "access_token" in res.url:
                    parse_token = parse_qs(urlparse(res.url).fragment)
                    lm4utils.setSetting("domain", domain)
                    lm4utils.setSetting("tenant", tenant)
                    lm4utils.setSetting("library", library)
                    lm4utils.setSetting("username", username)
                    lm4utils.setSetting("access_token", parse_token["access_token"][0])
                    lm4utils.setSetting(
                        "refresh_token", parse_token["refresh_token"][0]
                    )
                else:
                    lm4utils.displayMsg(
                        lm4utils.getTranslation(30506), lm4utils.getTranslation(30507)
                    )

            else:
                lm4utils.displayMsg(
                    lm4utils.getTranslation(30506), lm4utils.getTranslation(30511)
                )
        else:
            lm4utils.displayMsg(
                lm4utils.getTranslation(30506), lm4utils.getTranslation(30510)
            )

    else:
        files = {
            "client_id": (None, client_id),
            "provider": (None, provider),
            "username": (None, username),
            "password": (None, password),
        }
        j = requests.post(
            "https://api.vod.filmwerte.de/connect/authorize-external", files=files
        ).json()
        if "error" in j:
            if j["error"] == "InvalidCredentials":
                lm4utils.displayMsg(
                    lm4utils.getTranslation(30506), lm4utils.getTranslation(30508)
                )
            else:
                lm4utils.displayMsg(
                    lm4utils.getTranslation(30506), lm4utils.getTranslation(30507)
                )
            return

        lm4utils.setSetting("domain", domain)
        lm4utils.setSetting("tenant", tenant)
        lm4utils.setSetting("library", library)
        lm4utils.setSetting("username", username)
        lm4utils.setSetting("access_token", j["access_token"])
        lm4utils.setSetting("refresh_token", j["refresh_token"])
