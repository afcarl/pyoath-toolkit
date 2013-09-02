# -*- coding: utf-8 -*-
#
# Copyright 2013 Mark Lee
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
'''
`WTForms`_-related code for one-time password fields.

.. _WTForms: https://pypi.python.org/pypi/WTForms
'''

from __future__ import absolute_import

from . import OATH
from ._compat import to_bytes
from abc import ABCMeta, abstractmethod
import time
from wtforms import ValidationError


class OTPValidator(object):
    '''
    WTForms abstract base field validator for a OTP field.

    :param int digits: The expected number of digits in the OTP.
    :param int window: The number of OTPs before and after the start OTP
                       to test.
    :param bool verbose_errors: Whether to raise verbose validation errors.
    :param callable get_secret: If specified, a callable which returns the
                                OATH secret used to validate the OTP.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, digits, window, verbose_errors=False, get_secret=None):
        self.digits = digits
        self.window = window
        self.verbose = verbose_errors
        self.oath = OATH()
        self.get_secret = get_secret

    def get_oath_secret(self, form, field):
        '''
        Retrieves the OATH secret from a given form/field. Either uses the
        callback passed in when creating the validator, or the ``oath_secret``
        attribute of the ``user`` attribute of the ``form``.

        :rtype: bytes
        '''
        if self.get_secret:
            secret = self.get_secret(form, field)
        else:
            secret = form.user.oath_secret
        return to_bytes(secret)

    @abstractmethod
    def otp_validate(self, form, field):
        '''
        This should call the appropriate OTP validation method.

        :return: :data:`True` on success
        :raises: :class:`RuntimeError` on failure
        '''
        raise NotImplementedError

    def __call__(self, form, field):
        generic_error = field.gettext(u'OTP is invalid.')
        if not field.data:
            raise ValidationError(field.gettext(u'Field is required.'))
        elif len(field.data) != self.digits:
            if self.verbose:
                msg = field.gettext(u'OTP must be {digits} digits.')
            else:
                msg = generic_error
            raise ValidationError(msg.format(digits=self.digits))
        try:
            self.otp_validate(form, field)
        except RuntimeError as e:
            if self.verbose:
                msg = field.gettext('Error validating OTP: {err}')
            else:
                msg = generic_error
            raise ValidationError(msg.format(err=str(e)))


class HOTPValidator(OTPValidator):
    '''
    Validator for HOTP-based passwords.

    :param int digits: The expected number of digits in the OTP.
    :param int window: The number of OTPs before and after the start OTP
                       to test.
    :param int start_moving_factor: unsigned, can be :func:`long`, in theory.
    :param bool verbose_errors: Whether to raise verbose validation errors.
    :param callable get_secret: If specified, a callable which returns the
                                OATH secret used to validate the OTP.
    '''
    def __init__(self, digits, window, start_moving_factor,
                 verbose_errors=False, get_secret=None):
        super(HOTPValidator, self).__init__(digits, window, verbose_errors,
                                            get_secret)
        self.start_moving_factor = start_moving_factor

    def otp_validate(self, form, field):
        self.oath.hotp_validate(self.get_oath_secret(form, field),
                                self.start_moving_factor, self.window,
                                to_bytes(field.data))


class TOTPValidator(OTPValidator):
    '''
    Validator for TOTP-based passwords.

    :param int digits: The expected number of digits in the OTP.
    :param int window: The number of OTPs before and after the start OTP
                       to test.
    :param bool verbose_errors: Whether to raise verbose validation errors.
    :param callable get_secret: If specified, a callable which returns the
                                OATH secret used to validate the OTP.
    :param int start_time: The UNIX timestamp of when to start counting
                           time steps (usually should be ``0``).
    :param time_step_size: Unsigned, the time step system parameter. If
                           set to :data:`None`, defaults to ``30``.
    :type time_step_size: :func:`int` or :data:`None`
    '''
    def __init__(self, digits, window, verbose_errors=False, get_secret=None,
                 start_time=0, time_step_size=None):
        super(TOTPValidator, self).__init__(digits, window, verbose_errors,
                                            get_secret)
        self.start_time = int(start_time)
        self.time_step_size = time_step_size

    def otp_validate(self, form, field):
        self.oath.totp_validate(self.get_oath_secret(form, field), time.time(),
                                self.time_step_size, self.start_time,
                                self.window, to_bytes(field.data))
