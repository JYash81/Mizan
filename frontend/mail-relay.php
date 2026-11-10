<?php
/**
 * Mizan Secure Email Relay for Hostinger
 * 
 * Enables the Mizan cloud backend on Render (which blocks outbound SMTP ports 25, 465, 587)
 * to send transactional emails securely through Hostinger over HTTPS (Port 443).
 */

header("Content-Type: application/json; charset=UTF-8");
header("X-Content-Type-Options: nosniff");

// Pre-shared authentication secret
$EXPECTED_SECRET = getenv("MAIL_RELAY_SECRET") ?: "mizan-secure-mail-relay-key-2026-safe";
$authHeader = $_SERVER['HTTP_X_MAIL_SECRET'] ?? '';

if (!$authHeader || !hash_equals($EXPECTED_SECRET, $authHeader)) {
    http_response_code(403);
    echo json_encode(["error" => "Forbidden: Invalid mail relay secret."]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(["error" => "Method Not Allowed. POST required."]);
    exit;
}

$rawInput = file_get_contents("php://input");
$input = json_decode($rawInput, true);

if (!$input || empty($input['to']) || empty($input['subject'])) {
    http_response_code(400);
    echo json_encode(["error" => "Invalid payload. 'to' and 'subject' are required."]);
    exit;
}

$to = filter_var(trim($input['to']), FILTER_VALIDATE_EMAIL);
if (!$to) {
    http_response_code(400);
    echo json_encode(["error" => "Invalid recipient email address."]);
    exit;
}

$subject = trim($input['subject']);
$html = $input['html'] ?? '';
$text = $input['text'] ?? strip_tags($html);
$fromEmail = "llmguru@hennt.in";
$fromName = "Mizan Platform";

// Function 1: Direct SMTP over SSL to Hostinger (Port 443 is not used here; PHP inside Hostinger connects to Port 465 locally)
function sendViaHostingerSmtp($to, $subject, $text, $html, $fromEmail, $fromName) {
    $host = "smtp.hostinger.com";
    $port = 465;
    $user = "llmguru@hennt.in";
    $pass = 'yeswantH@181#';

    $context = stream_context_create([
        'ssl' => [
            'verify_peer' => true,
            'verify_peer_name' => true,
            'allow_self_signed' => false,
        ]
    ]);

    $socket = @stream_socket_client("ssl://{$host}:{$port}", $errno, $errstr, 15, STREAM_CLIENT_CONNECT, $context);
    if (!$socket) {
        return false;
    }

    $read = function() use ($socket) {
        $res = "";
        while ($str = fgets($socket, 515)) {
            $res .= $str;
            if (substr($str, 3, 1) === ' ') break;
        }
        return $res;
    };

    $write = function($cmd) use ($socket) {
        fputs($socket, $cmd . "\r\n");
    };

    $read();
    $write("EHLO llmguru.hennt.in");
    $read();
    $write("AUTH LOGIN");
    $read();
    $write(base64_encode($user));
    $read();
    $write(base64_encode($pass));
    $authResp = $read();

    if (strpos($authResp, '235') === false) {
        fclose($socket);
        return false;
    }

    $write("MAIL FROM: <{$fromEmail}>");
    $read();
    $write("RCPT TO: <{$to}>");
    $read();
    $write("DATA");
    $read();

    $boundary = md5(uniqid(microtime(true), true));
    $headers = "From: =?UTF-8?B?" . base64_encode($fromName) . "?= <{$fromEmail}>\r\n";
    $headers .= "To: <{$to}>\r\n";
    $headers .= "Subject: =?UTF-8?B?" . base64_encode($subject) . "?=\r\n";
    $headers .= "Date: " . date("r") . "\r\n";
    $headers .= "MIME-Version: 1.0\r\n";
    $headers .= "Content-Type: multipart/alternative; boundary=\"{$boundary}\"\r\n";

    $message = $headers . "\r\n";
    $message .= "--{$boundary}\r\n";
    $message .= "Content-Type: text/plain; charset=UTF-8\r\n";
    $message .= "Content-Transfer-Encoding: base64\r\n\r\n";
    $message .= chunk_split(base64_encode($text)) . "\r\n";

    if (!empty($html)) {
        $message .= "--{$boundary}\r\n";
        $message .= "Content-Type: text/html; charset=UTF-8\r\n";
        $message .= "Content-Transfer-Encoding: base64\r\n\r\n";
        $message .= chunk_split(base64_encode($html)) . "\r\n";
    }
    $message .= "--{$boundary}--\r\n";
    $message .= ".\r\n";

    $write($message);
    $dataResp = $read();
    $write("QUIT");
    fclose($socket);

    return strpos($dataResp, '250') !== false;
}

// Function 2: Native PHP mail() fallback
function sendViaNativeMail($to, $subject, $text, $html, $fromEmail, $fromName) {
    $boundary = md5(uniqid(microtime(true), true));
    $headers = "From: =?UTF-8?B?" . base64_encode($fromName) . "?= <{$fromEmail}>\r\n";
    $headers .= "Reply-To: {$fromEmail}\r\n";
    $headers .= "MIME-Version: 1.0\r\n";
    $headers .= "Content-Type: multipart/alternative; boundary=\"{$boundary}\"\r\n";

    $message = "--{$boundary}\r\n";
    $message .= "Content-Type: text/plain; charset=UTF-8\r\n";
    $message .= "Content-Transfer-Encoding: base64\r\n\r\n";
    $message .= chunk_split(base64_encode($text)) . "\r\n";

    if (!empty($html)) {
        $message .= "--{$boundary}\r\n";
        $message .= "Content-Type: text/html; charset=UTF-8\r\n";
        $message .= "Content-Transfer-Encoding: base64\r\n\r\n";
        $message .= chunk_split(base64_encode($html)) . "\r\n";
    }
    $message .= "--{$boundary}--\r\n";

    return @mail($to, $subject, $message, $headers, "-f{$fromEmail}");
}

// Attempt delivery via SMTP first, then native mail
$success = sendViaHostingerSmtp($to, $subject, $text, $html, $fromEmail, $fromName);
$method = "smtp_direct";

if (!$success) {
    $success = sendViaNativeMail($to, $subject, $text, $html, $fromEmail, $fromName);
    $method = "php_mail";
}

if ($success) {
    http_response_code(200);
    echo json_encode([
        "status" => "sent",
        "to" => $to,
        "method" => $method,
        "timestamp" => date("c"),
    ]);
} else {
    http_response_code(500);
    echo json_encode([
        "error" => "Email delivery failed on Hostinger.",
        "details" => "Both Hostinger SMTP and PHP mail() returned failure.",
    ]);
}
