/* Tavşan bildirim ve temel çevrimdışı önbellek */
importScripts('https://www.gstatic.com/firebasejs/11.10.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.10.0/firebase-messaging-compat.js');
firebase.initializeApp({apiKey:'AIzaSyD7t5srWWMQHFFA1cDBvLEAQoijLfGQ_lc',authDomain:'tavsan-44365.firebaseapp.com',projectId:'tavsan-44365',storageBucket:'tavsan-44365.firebasestorage.app',messagingSenderId:'112751591946',appId:'1:112751591946:web:c41c85452fc8bf355055f3'});
const messaging=firebase.messaging();
messaging.onBackgroundMessage(payload=>{if(payload.notification)return;const data=payload.data||{};self.registration.showNotification(data.title||'🌸 Tavşan', {body:data.body||'Hayırlı vakitler! Bir hatırlatman var.',icon:'./icon-192.png',badge:'./icon-192.png',data:{url:'./'},tag:data.tag||'tavsan-hatirlatma'});});
self.addEventListener('notificationclick',event=>{event.notification.close();event.waitUntil((async()=>{const url=new URL('./',self.registration.scope).href;const windows=await clients.matchAll({type:'window',includeUncontrolled:true});for(const w of windows){if(w.url.startsWith(self.registration.scope)){await w.focus();return}}await clients.openWindow(url)})())});
self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
