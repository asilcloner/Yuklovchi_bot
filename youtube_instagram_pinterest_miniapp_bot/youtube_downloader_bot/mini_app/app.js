const tg = window.Telegram?.WebApp;
const input = document.querySelector('#linkInput');
const pasteBtn = document.querySelector('#pasteBtn');
const sendBtn = document.querySelector('#sendBtn');
const statusEl = document.querySelector('#status');

if (tg) {
  tg.ready();
  tg.expand();
}

function setStatus(text) {
  statusEl.textContent = text;
}

function isSupportedLink(value) {
  try {
    const url = new URL(value);
    const host = url.hostname.replace(/^www\./, '').toLowerCase();
    return (
      host === 'youtu.be' ||
      host === 'youtube.com' ||
      host.endsWith('.youtube.com') ||
      host === 'instagram.com' ||
      host.endsWith('.instagram.com') ||
      host === 'pinterest.com' ||
      host.endsWith('.pinterest.com') ||
      host === 'pin.it'
    );
  } catch (_) {
    return false;
  }
}

pasteBtn.addEventListener('click', async () => {
  try {
    const text = await navigator.clipboard.readText();
    input.value = text.trim();
    setStatus('✅ Link qo‘yildi. Endi “Botga yuborish” ni bosing.');
  } catch (_) {
    setStatus('Clipboard o‘qilmadi. Linkni qo‘lda kiriting.');
  }
});

sendBtn.addEventListener('click', () => {
  const link = input.value.trim();

  if (!isSupportedLink(link)) {
    setStatus('❌ YouTube, Instagram yoki Pinterest link kiriting.');
    return;
  }

  if (tg?.sendData) {
    tg.sendData(link);
    setStatus('✅ Link botga yuborildi. Telegram chatga qayting.');
    setTimeout(() => tg.close(), 700);
  } else {
    navigator.clipboard?.writeText(link);
    setStatus('✅ Link clipboardga olindi. Uni bot chatiga yuboring.');
  }
});
