# -*- coding: utf-8 -*-
import base64
import codecs
import io
import json
import requests
import logging
import mimetypes
import re
from os.path import basename
from datetime import date, datetime, timedelta
import phonenumbers
from PIL import Image
from odoo import fields, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import image_process, image_to_base64, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)

TIMEOUT = (10, 20)
DEFAULT_IMAGE = 'placeholder.png'
DEFAULT_IMAGE_URL = '/web/static/img/' + DEFAULT_IMAGE


def log_request_error(param, req=None):
    try:
        param = json.dumps(param, indent=4, sort_keys=True, ensure_ascii=False)[:1000]
        if req is not None:
            _logger.error('\nSTATUS: %s\nSEND: %s\nRESULT: %s' %
                          (req.status_code, req.request.headers, req.text and req.text[:1000]))
    except Exception as _e:
        pass
    _logger.error(param, exc_info=True)


def date2sure_str(value):
    if isinstance(value, (date, datetime)):
        return fields.Datetime.to_string(value)
    else:
        return value


def date2sure_write(value):
    ''' To ORM format '''
    if isinstance(value, (date, datetime)):
        return value  # Odoo 14
        # return fields.Datetime.to_string(value)  # Old
    else:
        return fields.Datetime.to_datetime(value)  # Odoo 14
        # return value  # Old


def date2local(self, date_field):
    self_sudo = self if self.env.context.get('tz') or self.env.user.tz else self.with_user(SUPERUSER_ID)
    return fields.Datetime.context_timestamp(self_sudo, date_field)


def date2local_str(self, date_field, out='%Y-%m-%d %H:%M:%S'):
    local = date2local(self, date_field)
    return local.strftime(out)


def date_timedelta(minutes=False, days=False):
    '''
    :param minutes: integer
    :param days: integer
    :return: datetime
    '''
    # ret = fields.Datetime.subtract(fields.Datetime.now(), days=1)
    assert not(minutes and days), 'minutes or days please (as integer).'
    minutes = minutes or days * 24 * 60
    ret = datetime.now().replace(microsecond=0) + timedelta(minutes=minutes)
    return ret


def date_delta_seconds(date_field1, date_field2='now'):
    if not date_field1 or not date_field2:
        return 0
    d1 = date_field1
    if date_field2 == 'now':
        d2 = datetime.now()
    else:
        d2 = date_field2
    if not isinstance(d1, (date, datetime)):
        d1 = datetime.strptime(d1, DEFAULT_SERVER_DATETIME_FORMAT)
    if not isinstance(d2, (date, datetime)):
        d2 = datetime.strptime(d2, DEFAULT_SERVER_DATETIME_FORMAT)
    return int(abs((d1 - d2).total_seconds()))


def get_binary_attach(env, model, res_id, field, fields_ret=['mimetype']):
    attach = env['ir.attachment'].sudo().search_read(
        domain=[('res_model', '=', model), ('res_id', '=', res_id),
                ('res_field', '=', field)], fields=fields_ret,
        limit=1)
    return attach and attach[0]


def get_image_url(self, res_id, res_id_field, link_field='image_128', put_default=True):
    ''' get url from model image '''
    if res_id_field:
        unique = date2local_str(self, res_id.write_date, out='%d%m%Y%H%M%S')
        url = '/web/image?model=%s&id=%s&field=%s&unique=%s' % \
              (res_id._name, res_id.id, link_field, unique)
    else:
        url = False
        if put_default:
            url = DEFAULT_IMAGE_URL
    return url


def get_image_from_url(url, mimet=False):
    try:
        if not url or not isinstance(url, (str, bytes)) or not url.startswith('http'):
            return False
        r = requests.get(url, timeout=TIMEOUT)
        if not 200 <= r.status_code <= 299:
            return False
        datas = base64.b64encode(r.content)
        if mimet:
            if '; ' in r.headers['Content-Type']:
                ttype = mimetypes.guess_extension(r.headers['Content-Type'].split('; ')[0])
            else:
                ttype = mimetypes.guess_extension(r.headers['Content-Type'])
            return datas.decode(), ttype
        else:
            return datas.decode()
    except requests.exceptions.ConnectTimeout as _err:
        log_request_error(['get_image_from_url / ConnectTimeout', url])
        # raise Warning(_('Timeout error. Try again...'))
        return False
    except (requests.exceptions.HTTPError,
            requests.exceptions.RequestException,
            requests.exceptions.ConnectionError) as _err:
        log_request_error(['get_image_from_url / requests', url])
        # ex_type, ex_value, ex_traceback = sys.exc_info()
        # raise Warning(_('Error! Could not request image.\n%s') % ex_type)
        return False


def create_attachment_from_url(env, url, message_id, filename=False, headers=None):
    r = requests.get(url, timeout=TIMEOUT, headers=headers)
    datas = base64.b64encode(r.content)
    if filename:
        a, b, c = filename.rpartition('.')
        filename = filename if (a and b and c) else False
    if not filename:
        if r.headers['Content-Type'] == 'image/webp' or url.lower().endswith('.webp'):
            filename = 'sticker.webp'
    if not filename:
        if '; ' in r.headers['Content-Type']:
            mime = r.headers['Content-Type'].split('; ')[0]
        else:
            mime = r.headers['Content-Type']

        name_url = basename(url)
        a, b, ttype_url = name_url.rpartition('.')
        if a and b and ttype_url:
            ttype = '.%s' % ttype_url.split('?')[0]
        else:
            ttype = mimetypes.guess_extension(mime or '')

        ttype = (ttype or '').replace('jpeg', 'jpg').replace('jpe', 'jpg')
        mime = (mime or 'application').replace('application', message_id.ttype)
        filename = mime.split('/')[0] + ttype
    vals = {
        'name': filename,
        'datas': datas,
        'res_model': 'acrux.chat.message',
        'res_id': message_id.id,
        'delete_old': True,
    }
    return env['ir.attachment'].sudo().create(vals)


def clean_number(number):
    return re.sub('[^0123456789]', '', number or '')


def phone_info(env, number):
    '''
    :param number: valid number with code
    :return: phone_code, national_number, country_id
    '''
    try:
        number = number.lstrip(' +')
        nbr = phonenumbers.parse('+' + number)
        phone_code = nbr.country_code
        national_number = nbr.national_number
        country_code = phonenumbers.phonenumberutil.region_code_for_country_code(phone_code)
        country_id = env['res.country'].search([('code', '=', country_code)], limit=1)
        return phone_code, national_number, country_id
    except Exception as _e:
        return False, False, False


def phone_format(number, country_id=None, formatted=False, raise_error=True):
    '''
    :param number: string, with or without format
    From WhatsApp (Is valid number): country_id=None
        ( phone_format(self.number) )
    Manual entry: Add country_id
        ( phone_format(self.mobile, self.country_id) ) '''
    try:
        number = number.lstrip(' +')
        if country_id and len(country_id) == 1:
            code = country_id.phone_code
            region = country_id.code
        else:
            number = '+' + number
            code = None
            region = None
        nbr = phonenumbers.parse(number, region=region)
        if code and code != nbr.country_code:
            nbr = False
    except phonenumbers.phonenumberutil.NumberParseException as _e:
        nbr = False
    if nbr and not phonenumbers.is_possible_number(nbr):
        nbr = extra_phone_check(nbr)  # keep old config or new ?
    if not nbr:
        if raise_error:
            raise UserError(str(number) + _(' Invalid number.'))
        else:
            return False
    if formatted:
        format_number = phonenumbers.format_number(nbr, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    else:
        format_number = phonenumbers.format_number(nbr, phonenumbers.PhoneNumberFormat.E164)
    return format_number


def extra_phone_check(numobj):
    '''
        This method try to padding with zeros that numbers does not have them
    '''
    country_code = phonenumbers.region_code_for_number(numobj)
    out = False
    if country_code == 'CI':  # only case, it's generic if another country requirement
        types = phonenumbers.supported_types_for_region(country_code)
        if types:  # these are country phone test case
            bad_number = phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164)
            for ttype in list(types):  # for all test case try to find a valid case
                tmp_number = None
                good_number = phonenumbers.example_number_for_type(country_code, ttype)  # example a valid number
                # if number allow leading zero then add zero to original number
                if good_number.italian_leading_zero or good_number.number_of_leading_zeros:
                    good_number = phonenumbers.format_number(good_number, phonenumbers.PhoneNumberFormat.E164)
                    if len(bad_number) < len(good_number):  # if original number missing zeros
                        padding_zero = len(good_number) - len(str(numobj.country_code)) - 1
                        new_number = '+%s%s' % (numobj.country_code, str(numobj.national_number).rjust(padding_zero, '0'))
                        tmp_number = phonenumbers.parse(new_number)
                else:
                    tmp_number = numobj
                if tmp_number and phonenumbers.is_possible_number_for_type(tmp_number, ttype):
                    out = tmp_number  # a valid test case was found
                    break
    return out


def image2jpg(env, content):
    if not content:
        return False
    if isinstance(content, str):
        content = content.encode('ascii')

    config_size = env['ir.config_parameter'].sudo().get_param('acrux_image_resize', 500)
    if config_size == 'original':
        size = (0, 0)
    else:
        size = (min(int(config_size), 1024), min(int(config_size), 1024))
    try:
        ret = image_process(content, size=size, quality=80, output_format='JPEG')
    except IOError as _e:
        image_stream = io.BytesIO(codecs.decode(content, 'base64'))
        image = Image.open(image_stream)
        if image.mode == 'P':
            if 'transparency' in image.info:
                alpha = image.convert('RGBA').split()[-1]
                bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
                bg.paste(image, mask=alpha)
            image = image.convert('RGB')
        opt = {'format': 'JPEG', 'optimize': True, 'quality': 80}
        # stream = io.BytesIO()
        # image.save(stream, **opt)

        to_base64 = image_to_base64(image, **opt)
        ret = image_process(to_base64, size=size, quality=80, output_format='JPEG')
    except Exception as _e:
        ret = False
        _logger.error('Could not convert image to JPG.')

    return ret
