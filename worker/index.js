/**
 * Feishu Document Proxy Worker
 * 
 * Endpoints:
 *   GET /api/doc?url=<feishu_doc_url>   → returns structured blocks JSON
 *   GET /api/image?token=<file_token>    → proxies feishu image download
 *
 * Environment variables (secrets):
 *   FEISHU_APP_ID
 *   FEISHU_APP_SECRET
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

async function getTenantAccessToken(appId, appSecret) {
  const res = await fetch('https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app_id: appId, app_secret: appSecret }),
  });
  const data = await res.json();
  if (data.code !== 0 || !data.tenant_access_token) {
    throw new Error(`获取 tenant_access_token 失败: ${data.msg || JSON.stringify(data)}`);
  }
  return data.tenant_access_token;
}

function extractDocId(url) {
  // Support patterns:
  //   https://xxx.feishu.cn/docx/TOKEN
  //   https://xxx.feishu.cn/docx/TOKEN?...
  //   https://xxx.larksuite.com/docx/TOKEN
  const m = url.match(/\/docx\/([A-Za-z0-9]+)/);
  return m ? m[1] : null;
}

async function fetchAllBlocks(docId, token) {
  let allBlocks = [];
  let pageToken = '';
  do {
    const url = `https://open.feishu.cn/open-apis/docx/v1/documents/${docId}/blocks?page_size=500${pageToken ? '&page_token=' + pageToken : ''}`;
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    const data = await res.json();
    if (data.code !== 0) {
      throw new Error(`获取文档 blocks 失败: ${data.msg || JSON.stringify(data)}`);
    }
    if (data.data && data.data.items) {
      allBlocks = allBlocks.concat(data.data.items);
    }
    pageToken = (data.data && data.data.page_token) || '';
  } while (pageToken);
  return allBlocks;
}

function extractTextFromElements(obj) {
  if (!obj || !obj.elements) return '';
  return obj.elements.map(e => {
    if (e.text_run) return e.text_run.content || '';
    if (e.mention_user) return '';
    if (e.mention_doc) return '';
    return '';
  }).join('');
}

function parseBlocks(allBlocks, workerOrigin) {
  const result = [];
  // Build a map for parent-child relationships (callout children)
  const blockMap = new Map();
  allBlocks.forEach(b => blockMap.set(b.block_id, b));

  for (const block of allBlocks) {
    const type = block.block_type;

    // 1=page (document root) — skip
    if (type === 1) continue;

    // 2=text
    if (type === 2) {
      const text = extractTextFromElements(block.text);
      if (text.trim()) result.push({ type: 'text', text });
      continue;
    }

    // 3=heading1
    if (type === 3) {
      const text = extractTextFromElements(block.heading1);
      if (text.trim()) result.push({ type: 'chapter', text });
      continue;
    }

    // 4=heading2
    if (type === 4) {
      const text = extractTextFromElements(block.heading2);
      if (text.trim()) result.push({ type: 'section', text });
      continue;
    }

    // 5=heading3
    if (type === 5) {
      const text = extractTextFromElements(block.heading3);
      if (text.trim()) result.push({ type: 'case', text });
      continue;
    }

    // 6=heading4, 7=heading5, 8=heading6 — map to case
    if (type >= 6 && type <= 8) {
      const key = `heading${type - 3}`;
      const text = extractTextFromElements(block[key]);
      if (text.trim()) result.push({ type: 'case', text });
      continue;
    }

    // 9=unordered_list, 10=ordered_list — extract text
    if (type === 9 || type === 10) {
      const key = type === 9 ? 'unordered_list' : 'ordered_list';
      const text = extractTextFromElements(block[key]);
      if (text.trim()) result.push({ type: 'text', text: '· ' + text });
      continue;
    }

    // 11=code — extract as callout
    if (type === 11) {
      const text = extractTextFromElements(block.code);
      if (text.trim()) result.push({ type: 'callout', text });
      continue;
    }

    // 13=quote_container — skip (children will be processed individually)
    if (type === 13) continue;

    // 12=quote — extract as highlight
    if (type === 12) {
      const text = extractTextFromElements(block.quote);
      if (text.trim()) result.push({ type: 'highlight', text });
      continue;
    }

    // 14=divider
    if (type === 14) {
      result.push({ type: 'divider' });
      continue;
    }

    // 27=image
    if (type === 27) {
      const fileToken = block.image && block.image.token;
      if (fileToken) {
        // Return proxy URL for the image
        const imgUrl = `${workerOrigin}/api/image?token=${encodeURIComponent(fileToken)}`;
        result.push({ type: 'image', src: imgUrl, fileToken });
      }
      continue;
    }

    // 34=callout — collect text from its children
    if (type === 34) {
      const childIds = block.children || [];
      const texts = [];
      for (const cid of childIds) {
        const child = blockMap.get(cid);
        if (!child) continue;
        // Extract text from child blocks of any type
        const ct = child.block_type;
        let childText = '';
        if (ct === 2) childText = extractTextFromElements(child.text);
        else if (ct === 3) childText = extractTextFromElements(child.heading1);
        else if (ct === 4) childText = extractTextFromElements(child.heading2);
        else if (ct === 5) childText = extractTextFromElements(child.heading3);
        if (childText.trim()) texts.push(childText.trim());
      }
      if (texts.length > 0) {
        result.push({ type: 'highlight', text: texts.join('\n') });
      }
      continue;
    }

    // 17=todo — extract text
    if (type === 17) {
      const text = extractTextFromElements(block.todo);
      if (text.trim()) result.push({ type: 'text', text: '☐ ' + text });
      continue;
    }

    // Other types: try to extract any text content
    // Skip silently if no recognizable content
  }

  return result;
}

async function handleDocRequest(url, env, workerOrigin) {
  const docId = extractDocId(url);
  if (!docId) {
    return jsonResponse({ error: '无效的飞书文档链接，需要 /docx/TOKEN 格式' }, 400);
  }

  try {
    const token = await getTenantAccessToken(env.FEISHU_APP_ID, env.FEISHU_APP_SECRET);
    const allBlocks = await fetchAllBlocks(docId, token);
    const blocks = parseBlocks(allBlocks, workerOrigin);
    return jsonResponse({ ok: true, blocks });
  } catch (e) {
    return jsonResponse({ error: e.message }, 500);
  }
}

async function handleImageRequest(fileToken, env) {
  if (!fileToken) {
    return jsonResponse({ error: '缺少 token 参数' }, 400);
  }

  try {
    const token = await getTenantAccessToken(env.FEISHU_APP_ID, env.FEISHU_APP_SECRET);
    const imgRes = await fetch(`https://open.feishu.cn/open-apis/drive/v1/medias/${fileToken}/download`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!imgRes.ok) {
      return jsonResponse({ error: `图片下载失败: ${imgRes.status}` }, 502);
    }

    const contentType = imgRes.headers.get('content-type') || 'image/png';
    const body = imgRes.body;

    return new Response(body, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
        ...CORS_HEADERS,
      },
    });
  } catch (e) {
    return jsonResponse({ error: e.message }, 500);
  }
}

export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const workerOrigin = url.origin;

    if (url.pathname === '/api/doc') {
      const docUrl = url.searchParams.get('url');
      if (!docUrl) return jsonResponse({ error: '缺少 url 参数' }, 400);
      return handleDocRequest(docUrl, env, workerOrigin);
    }

    if (url.pathname === '/api/image') {
      const fileToken = url.searchParams.get('token');
      return handleImageRequest(fileToken, env);
    }

    // Health check
    if (url.pathname === '/') {
      return jsonResponse({ status: 'ok', service: 'feishu-doc-proxy' });
    }

    return jsonResponse({ error: 'Not found' }, 404);
  },
};
