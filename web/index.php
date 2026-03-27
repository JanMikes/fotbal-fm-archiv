<?php
/**
 * MFK Frýdek-Místek Archive Router
 *
 * Routes .asp URLs with query parameters to stored HTML files.
 * Usage: php -S localhost:8000 index.php   (run from web/ directory)
 */

// For PHP built-in server: return false for actual files so they're served directly
if (php_sapi_name() === 'cli-server') {
    $filePath = __DIR__ . '/' . ltrim(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH), '/');
    if (is_file($filePath)) {
        return false; // Let the built-in server handle it
    }
}

// Load page map (cached in APCu if available)
$mapFile = __DIR__ . '/page_map.json';
$pageMap = null;

if (function_exists('apcu_fetch')) {
    $pageMap = apcu_fetch('page_map');
}

if (!$pageMap) {
    if (!file_exists($mapFile)) {
        http_response_code(500);
        echo "page_map.json not found. Run the scraper first.";
        exit;
    }
    $pageMap = json_decode(file_get_contents($mapFile), true);
    if (!$pageMap) {
        http_response_code(500);
        echo "Failed to parse page_map.json";
        exit;
    }
    if (function_exists('apcu_store')) {
        apcu_store('page_map', $pageMap, 3600);
    }
}

// Get request info
$requestUri = $_SERVER['REQUEST_URI'] ?? '/';
$parsedUrl = parse_url($requestUri);
$path = ltrim($parsedUrl['path'] ?? '/', '/');
$queryString = $parsedUrl['query'] ?? '';

// Handle bare root
if ($path === '' || $path === '/') {
    $path = 'index.asp';
}

// Serve static assets
$assetPrefixes = ['img/', 'foto/', 'znaky/', 'ads/', 'soubory/', 'inc/', 'css/', 'assets/'];
foreach ($assetPrefixes as $prefix) {
    if (strpos($path, $prefix) === 0) {
        if (strpos($path, 'assets/') === 0) {
            $assetPath = __DIR__ . '/' . $path;
        } else {
            $assetPath = __DIR__ . '/assets/' . $path;
        }

        // Prevent directory traversal
        $realPath = realpath($assetPath);
        $assetsRoot = realpath(__DIR__ . '/assets');
        if ($realPath && $assetsRoot && strpos($realPath, $assetsRoot) === 0 && is_file($realPath)) {
            $ext = strtolower(pathinfo($realPath, PATHINFO_EXTENSION));
            $mimeTypes = [
                'html' => 'text/html', 'css' => 'text/css', 'js' => 'application/javascript',
                'json' => 'application/json', 'png' => 'image/png', 'jpg' => 'image/jpeg',
                'jpeg' => 'image/jpeg', 'gif' => 'image/gif', 'svg' => 'image/svg+xml',
                'ico' => 'image/x-icon', 'pdf' => 'application/pdf', 'doc' => 'application/msword',
                'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'xls' => 'application/vnd.ms-excel', 'zip' => 'application/zip',
                'woff' => 'font/woff', 'woff2' => 'font/woff2', 'ttf' => 'font/ttf',
                'min' => 'text/css', // .min files are often CSS
            ];
            $contentType = $mimeTypes[$ext] ?? 'application/octet-stream';
            header("Content-Type: $contentType");
            header("Content-Length: " . filesize($realPath));
            header("Cache-Control: public, max-age=86400");
            readfile($realPath);
            exit;
        }

        http_response_code(404);
        exit;
    }
}

// Build canonical URL key for page map lookup
function buildKey(string $path, string $queryString): string {
    if (empty($queryString)) {
        return $path;
    }
    parse_str($queryString, $params);
    $params = array_filter($params, function($v) {
        return $v !== '' && $v !== null;
    });
    ksort($params);
    $qs = http_build_query($params);
    return $qs ? "{$path}?{$qs}" : $path;
}

function servePage(array $pageMap, string $key): bool {
    if (isset($pageMap[$key]) && !empty($pageMap[$key]['file']) && $pageMap[$key]['status'] == 200) {
        $htmlFile = __DIR__ . '/' . $pageMap[$key]['file'];
        if (file_exists($htmlFile)) {
            header('Content-Type: text/html; charset=utf-8');
            readfile($htmlFile);
            return true;
        }
    }
    return false;
}

// Try exact match with normalized key
$key = buildKey($path, $queryString);
if (servePage($pageMap, $key)) exit;

// Try raw query string (un-normalized)
$rawKey = $queryString ? "{$path}?{$queryString}" : $path;
if ($rawKey !== $key && servePage($pageMap, $rawKey)) exit;

// Try partial match: strip extra params progressively
if ($queryString) {
    parse_str($queryString, $params);
    $keys = array_keys($params);
    for ($i = count($keys); $i >= 1; $i--) {
        $subset = array_slice($params, 0, $i);
        ksort($subset);
        $subset = array_filter($subset, function($v) { return $v !== '' && $v !== null; });
        $tryQs = http_build_query($subset);
        $tryKey = $tryQs ? "{$path}?{$tryQs}" : $path;
        if ($tryKey !== $key && servePage($pageMap, $tryKey)) exit;
    }
}

// Try without query string (fallback)
if ($queryString && servePage($pageMap, $path)) exit;

// 404
http_response_code(404);
?>
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="utf-8">
    <title>Stránka nenalezena - MFK Frýdek-Místek Archiv</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a2e; color: #fff; }
        h1 { color: #e94560; }
        a { color: #0f3460; background: #e94560; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }
        a:hover { background: #c73e54; }
        .url { color: #888; font-size: 14px; margin-top: 20px; word-break: break-all; }
    </style>
</head>
<body>
    <h1>404 - Stránka nenalezena</h1>
    <p>Tato stránka nebyla nalezena v archivu webu MFK Frýdek-Místek.</p>
    <a href="/index.asp">Zpět na úvodní stránku</a>
    <p class="url">Hledaná stránka: <?= htmlspecialchars($requestUri) ?></p>
</body>
</html>
