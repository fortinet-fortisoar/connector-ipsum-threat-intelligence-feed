"""
Copyright start
MIT License
Copyright (c) 2024 Fortinet Inc
Copyright end
"""

import requests
from connectors.core.connector import get_logger, ConnectorError

try:
    from integrations.crudhub import trigger_ingest_playbook
except:
    # ignore. lower FSR version
    pass

logger = get_logger('ipsum-threat-intelligence-feed')


class IPsumTIFeed(object):
    def __init__(self, config, *args, **kwargs):
        self.url = config.get('server_url').strip('/')
        self.verify_ssl = config.get('verify_ssl')

    def make_rest_call(self, method='GET', data=None, params=None):
        try:
            url = self.url
            response = requests.request(method, url, data=data, params=params, verify=self.verify_ssl,
                                        timeout=60)
            if response.ok:
                return response.text
            else:
                logger.error("{0}".format(response.status_code))
                raise ConnectorError("{0}:{1}".format(response.status_code, response.text))
        except requests.exceptions.SSLError:
            raise ConnectorError('SSL certificate validation failed')
        except requests.exceptions.ConnectTimeout:
            raise ConnectorError('The request timed out while trying to connect to the server')
        except requests.exceptions.ReadTimeout:
            raise ConnectorError(
                'The server did not send any data in the allotted amount of time')
        except requests.exceptions.ConnectionError:
            raise ConnectorError('Invalid Credentials')
        except Exception as err:
            raise ConnectorError(str(err))


def get_indicators(config, params, **kwargs):
    try:
        ipsum = IPsumTIFeed(config)
        feeds = []
        response = ipsum.make_rest_call()
        if response:
            filtered_indicators = {'last_updated': response.split("\n")[3].split(":")[1].strip()}
            for ip in response.split("\n")[7:-1]:
                blacklist_ip = ip.split("\t")
                feeds.append({'ip': blacklist_ip[0], 'count': blacklist_ip[1]})
            filtered_indicators.update({'feeds': feeds})
        else:
            filtered_indicators = {'feeds': []}
        mode = params.get('output_mode')
        if mode == 'Create as Feed Records in FortiSOAR':
            filtered_indicators = filtered_indicators.get('feeds')
            create_pb_id = params.get("create_pb_id")
            trigger_ingest_playbook(filtered_indicators, create_pb_id, parent_env=kwargs.get('env', {}),
                                    batch_size=1000)
        else:
            return filtered_indicators
    except Exception as err:
        raise ConnectorError(str(err))


def check_health(config, **kwargs):
    try:
        response = get_indicators(config, params={}, **kwargs)
        if response:
            return True
    except Exception as err:
        logger.info(str(err))
        raise ConnectorError(str(err))


operations = {
    'get_indicators': get_indicators
}
