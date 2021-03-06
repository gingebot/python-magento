import xmlrpclib

__all__ = ["MagentoAPI"]

class MagentoAPI(object):
    PATH = "/magento/api/xmlrpc"

    def __init__(self, host, port, api_user, api_key, path=None, allow_none=False, verbose=False, https=False):
        """Logs the client into Magento's API and discovers methods available
        to it. Throws an exception if logging in fails."""
        if https:
            self._proto = 'https'
        else:
            self._proto = 'http'

        if path is None:
            path = MagentoAPI.PATH
        self._api_user = api_user
        self._api_key = api_key
        self._host = host
        self._port = str(port)
        self._uri = "%s://%s:%s" % (self._proto, self._host, self._port) + path

        self._client = xmlrpclib.ServerProxy(self._uri, allow_none=allow_none, verbose=verbose)
        self.login()

    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self.end_session()

    def _discover(self):
        """Discovers methods in the XML-RPC API and creates attributes for them
        on this object. Enables stuff like "magento.cart.create(...)" to work
        without having to define Python methods for each XML-RPC equivalent."""

        self._resources = {}
        resources = self._client.resources(self._session_id)
        for resource in resources:
            self._resources[resource["name"]] = MagentoResource(
                self._client, self._session_id, resource["name"], 
                resource["title"], resource["methods"])

    def _get_client(self):
        """Returns the XML-RPC client, an xmlrpclib.ServerProxy (see Python docs)
        instance that's connected to the Magento API. Nice for debugging."""
        return self._client

    def _get_session_id(self):
        """Returns the cart session ID. You'll need it for debugging if you're
        sending calls through the client you receive by calling _get_client."""
        return self._session_id

    def __getattr__(self, name):
        """Intercepts valid Magento paths (e.g. "cart.create") to return functions
        that make a valid path's corresponding API call to the Magento server."""
        if name in self._resources:
            return self._resources[name]
        else:
            raise AttributeError

    def login(self):
        self._session_id = self._client.login(self._api_user, self._api_key)
        self._discover()

    def end_session(self):
        self._client.endSession(self._session_id)

    def keep_session_alive(self):
        """If the session expired, logs back in."""
        try:
            self.resources()
        except xmlrpclib.Fault as fault:
            if fault.faultCode == 5:
                self.login()
            else:
                raise

    def resources(self):
        """Calls the 'resources' Magento API method. From the Magento docs:
        
        'Return a list of available API resources and methods allowed for the 
        current session.'"""
        return self._client.resources(self._session_id)

    def global_faults(self):
        """Calls the 'globalFaults' Magento API method. From the Magento docs:

        'Return a list of fault messages and their codes that do not depend on 
        any resource.'"""
        return self._client.globalFaults(self._session_id)

    def resource_faults(self, resource_name):
        """Calls the 'resourceFaults' Magento API method. From the Magento docs:
        
        'Return a list of the specified resource fault messages, if this 
        resource is allowed in the current session.'"""
        return self._client.resourceFaults(self._session_id, resource_name)

    def help(self):
        """Prints discovered resources and their associated methods. Nice when 
        noodling in the terminal to wrap your head around Magento's insanity."""
        print "Resources:"
        print
        for name in sorted(self._resources.keys()):
            methods = sorted(self._resources[name]._methods.keys())
            print "%s: %s" % (bold(name), ", ".join(methods))

    def get_host(self):
        return self._host
    
    def get_port(self):
        return self._port
    
    def get_api_user(self):
        return self._api_user
    
    def get_api_key(self):
        return self._api_key

class MagentoResource(object):
    def __init__(self, client, session_id, name, title, methods):
        self._client = client
        self._session_id = session_id
        self._name = name
        self._title = title
        self._methods = {}
        
        for method in methods:
            self._methods[method["name"]] = method

    def __getattr__(self, name):
        if name in self._methods:
            return self._get_method_call(name)
        else:
            raise AttributeError
        
    def _get_method_call(self, method_name):
        path = ".".join([self._name, method_name])
        def call_method(*args, **kwargs):
            return self._client.call(self._session_id, path, args)
        return call_method

    def help(self):
        print "%s: %s" % (bold(self._name), self._title)
        for method in sorted(self._methods.keys()):
            print "  - %s: %s" % (bold(method), self._methods[method]["title"])

# Some text formatting stuff for the shell.
def bold(text):
    return u'\033[1m%s\033[0m' % text
