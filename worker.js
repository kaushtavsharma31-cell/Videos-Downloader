export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // API routes that need to be proxied to the Python Flask backend
    const apiRoutes = [
      '/download',
      '/downloads',
      '/download-file',
      '/clear-downloads',
      '/get-ip',
      '/supported-platforms'
    ];

    const isApiRoute = apiRoutes.some(route => path.startsWith(route));

    if (isApiRoute) {
      const backendUrl = env.BACKEND_API_URL || 'http://localhost:5000';
      const targetUrl = new URL(backendUrl);
      targetUrl.pathname = path;
      targetUrl.search = url.search;

      // Prepare request headers
      const headers = new Headers(request.headers);
      headers.set('Host', targetUrl.host);

      // Clone and build the proxy request
      const proxyRequest = new Request(targetUrl.toString(), {
        method: request.method,
        headers: headers,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.clone().blob() : null,
        redirect: 'manual'
      });

      try {
        const response = await fetch(proxyRequest);
        
        // Clone response and append CORS headers
        const newHeaders = new Headers(response.headers);
        newHeaders.set('Access-Control-Allow-Origin', '*');
        newHeaders.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE');
        newHeaders.set('Access-Control-Allow-Headers', '*');

        return new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers: newHeaders
        });
      } catch (err) {
        return new Response(JSON.stringify({ 
          status: 'error', 
          message: `Worker failed to connect to Flask backend: ${err.message}. Please check if BACKEND_API_URL is active.` 
        }), {
          status: 502,
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          }
        });
      }
    }

    // Handle OPTIONS requests (for CORS preflight checks)
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, DELETE',
          'Access-Control-Allow-Headers': '*',
          'Max-Age': '86400'
        }
      });
    }

    // Handle clean URLs mapping:
    // e.g. /about-us -> /about_us.html
    const cleanUrls = {
      '/about-us': '/about_us.html',
      '/contact-us': '/contact_us.html',
      '/privacy-policy': '/privacy_policy.html',
      '/terms-conditions': '/terms_conditions.html'
    };

    if (cleanUrls[path]) {
      const assetUrl = new URL(cleanUrls[path], request.url);
      return env.ASSETS.fetch(assetUrl);
    }

    // Default: Fallback to serving the static assets
    return env.ASSETS.fetch(request);
  }
};
