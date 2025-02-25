#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import datetime
import hashlib
import json
import logging
import os
import re
import uuid
from argparse import ArgumentParser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer

from scoring import get_interests, get_score

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class MyMeta(type):
    def __call__(cls, val, required, nullable, dct=None):
        return super().__call__(val, required, nullable, dct)


class CharField(metaclass=MyMeta):
    required: bool
    nullable: bool

    def __init__(self, val, required, nullable, dct=None):
        value = dct
        if dct is not None and isinstance(dct, dict):
            try:
                value = dct.get(val).get(val)
            except ValueError:
                pass

        if required and value is None:
            raise ValueError(get_error_response(f"Field {val} is required"))
        if not nullable and (val is None or value == ""):
            raise ValueError(get_error_response(f"Field {val} is required"))
        self.val = value


class ArgumentsField(metaclass=MyMeta):
    def __init__(self, val, required, nullable, dct=None):
        value = ""
        try:
            value = dct.get(val).get(val)
        except ValueError:
            pass
        if required and not nullable and (value == "" or value is None):
            raise ValueError(get_error_response(f"Field {val} is required"))
        if not nullable and (val is None or value == ""):
            raise ValueError(get_error_response(f"Field {val} is required"))
        if not isinstance(value, dict):
            raise ValueError(get_error_response(f"Field {val} must be a dict"))
        self.val = value


class EmailField(metaclass=MyMeta):
    def __init__(self, val, required, nullable, dct=None):
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, str(dct)) and dct is not None:
            raise ValueError(
                get_error_response("Поле email содержит недопустимые символы")
            )
        self.val = dct


class PhoneField(metaclass=MyMeta):
    def __init__(self, val, required, nullable, dct=None):
        if required and dct is None:
            raise ValueError(get_error_response(f"Field {val} is required"))
        if dct is not None:
            if not isinstance(int(dct), int) or (
                len(str(dct)) != 11 or int(str(dct)[0]) != 7
            ):
                raise ValueError(
                    get_error_response("Поле phone содержит недопустимые символы")
                )
        self.val = dct


class DateField(metaclass=MyMeta):
    def __init__(self, val, required, nullable, dct=None):

        date_field = dct
        if required and date_field is None:
            raise ValueError(get_error_response(f"Field {val} is required"))

        if dct is not None:
            try:
                date_field = date_format_validate(dct)
            except ValueError:
                raise ValueError(
                    get_error_response("Поле date содержит недопустимые символы")
                )
        self.val = date_field


class BirthDayField(metaclass=MyMeta):
    def __init__(self, val, required, nullable, dct=None):
        birthday = dct
        if birthday is not None:
            try:
                birthday = date_format_validate(dct)
                if datetime.datetime.today().year - birthday.year >= 70:
                    raise ValueError(get_error_response("Дата рождения больше 70 лет"))
            except ValueError as e:
                raise ValueError(e.args[0])
        self.val = birthday


class GenderField(metaclass=MyMeta):
    def __init__(self, val, required, nullable, dct=None):
        if dct not in [0, 1, 2] and dct is not None:
            raise ValueError(
                get_error_response("Поле gender содержит недопустимые символы")
            )
        self.val = dct


class ClientIDsField(metaclass=MyMeta):
    def __init__(self, val, required, nullable, dct=None):
        if (dct is None or not dct) or (
            not isinstance(dct, list) or not all(isinstance(i, int) for i in dct)
        ):
            raise ValueError(
                get_error_response("Поле client_ids содержит недопустимые символы")
            )
        self.val = dct


class ClientsInterestsRequest(object):
    def __init__(self, args):
        self.client_ids = ClientIDsField(
            required=True, nullable=True, val="client_ids", dct=args.get("client_ids")
        ).val
        self.date = DateField(
            required=False, nullable=True, val="date", dct=args.get("date")
        ).val


class OnlineScoreRequest(object):
    def __init__(self, request):
        args = request.get("body").get("arguments")
        self.first_name = CharField(
            required=False, nullable=True, val="first_name", dct=args.get("first_name")
        ).val
        self.last_name = CharField(
            required=False, nullable=True, val="last_name", dct=args.get("last_name")
        ).val
        self.email = EmailField(
            required=False, nullable=True, val="email", dct=args.get("email")
        ).val
        self.phone = PhoneField(
            required=False, nullable=True, val="phone", dct=args.get("phone")
        ).val
        self.birthday = BirthDayField(
            required=False, nullable=True, val="birthday", dct=args.get("birthday")
        ).val
        self.gender = GenderField(
            required=False, nullable=True, val="gender", dct=args.get("gender")
        ).val

        count_inconsistency = 0

        if self.phone is None or self.email is None:
            count_inconsistency += 1
        if self.first_name is None or self.last_name is None:
            count_inconsistency += 1
        if self.gender is None or self.birthday is None:
            count_inconsistency += 1

        if count_inconsistency == 3:
            raise ValueError(
                get_error_response(
                    "Одна из обязательных пар полей не заполнена", INVALID_REQUEST
                )
            )

        if (not str(self.first_name).isalpha() and self.first_name != "") or (
            not str(self.last_name).isalpha() and self.last_name != ""
        ):
            raise ValueError(
                get_error_response(
                    "Поле имени или фамилии содержит недопустимые символы",
                    INVALID_REQUEST,
                )
            )


class MethodRequest(object):
    excs: dict = {}

    def __init__(self, request):
        try:
            body = request.get("body")
            if bool(body) is False:
                raise ValueError({INVALID_REQUEST: ERRORS.get(INVALID_REQUEST)})
        except Exception as e:
            raise ValueError({INVALID_REQUEST: ERRORS.get(INVALID_REQUEST)})
        try:
            self.account = CharField(
                required=False, nullable=True, val="account", dct={"account": body}
            ).val
            self.login = CharField(
                required=True, nullable=True, val="login", dct={"login": body}
            ).val
            self.token = CharField(
                required=True, nullable=True, val="token", dct={"token": body}
            ).val
            self.arguments = ArgumentsField(
                required=True, nullable=True, val="arguments", dct={"arguments": body}
            ).val
            self.method = CharField(
                required=True, nullable=False, val="method", dct={"method": body}
            ).val
        except ValueError as e:
            raise ValueError({INVALID_REQUEST: ERRORS.get(INVALID_REQUEST)})

        if not check_auth(self):
            raise ValueError({FORBIDDEN: ERRORS.get(FORBIDDEN)})

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def get_error_response(error_text, code=INVALID_REQUEST):
    class ErrorResponse:
        def __init__(self, text: str):
            self.error: str = text

    response = {code: ErrorResponse(error_text).__dict__}
    logging.error(f"Ошибка: {error_text}")
    return response


def date_format_validate(date) -> datetime.datetime:
    return datetime.datetime.strptime(str(date), "%d.%m.%Y")


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        digest = hashlib.sha512(
            (request.account + request.login + SALT).encode("utf-8")
        ).hexdigest()
    return digest == request.token


def check_method_request(body):
    if not body.get("body").get("method") in [
        "online_score",
        "clients_interests",
    ]:
        return get_error_response("Метода не существует"), INVALID_REQUEST
    return "", OK


def get_filled_fields(obj: object) -> list:
    fields = []
    for key, value in obj.__dict__.items():
        if value is not None:
            fields.append(key)
    return fields[:]


def method_handler(request, ctx, store):
    try:
        method_request = MethodRequest(request)
    except ValueError as e:
        v1 = list(e.args[0].values())[0]
        v2 = list(e.args[0].keys())[0]
        return v1, v2

    match method_request.method:  # type: ignore[syntax]
        case "online_score":
            try:
                s = OnlineScoreRequest(request)
            except Exception as e:
                return e.args[0], INVALID_REQUEST

            ctx["has"] = get_filled_fields(s)
            score = get_score(
                store=store,
                phone=s.phone,
                email=s.email,
                birthday=s.birthday,
                gender=s.gender,
                first_name=s.first_name,
                last_name=s.last_name,
            )
            return score, OK
        case "clients_interests":
            try:
                client_inter = ClientsInterestsRequest(
                    dict(request.get("body").get("arguments"))
                )
            except Exception as e:
                return e.args[0], INVALID_REQUEST
            ctx["nclients"] = len(client_inter.client_ids)
            return get_interests(store=store, cid=client_inter.client_ids), OK
    return "", OK


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {"method": method_handler}
    store = None

    def get_request_id(self, headers):
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers}, context, self.store
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))
        return


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()

    if args.log:
        open(args.log, "a").close()

    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )
    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info("Starting server at %s" % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
