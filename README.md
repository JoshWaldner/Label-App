# Label-App
a Fusion addin to export labels to a visual layout app reader

I finally created an app to visually show the CNC operator which parts he looks at when cutting and unloading. I have been frusterated with fusions lack of capability to provide simple zebra labels for its parts when nesting, so I decided to make it meself. While not exactly printing zebra labels, it is easy to implement it. I know this app is very primitive and i might or might not work on it in the future, but as it is right now it works perfect. 

to make it work for you follow these steps:

1. paste the LabelCNCApp folder in your "C:\Users\{yourName}\Documents
2. run the server
3. install the fusion addin as you normally would install any fusion addin
4. install the Android app

A point to remember, I didnt make it super easy and plug and play. It might or might not run on the first try, and may need some corrections in the code, but any developer should be able to make it work. The main workflow is:
1. export json from fusion into a specific folder
2. server allows you to access this same data and serves the web app and the android app at the same time.
3. make sure whitelist and settings have correct information
4. open http:\\{yourcomputerip}:8000 on your browser
5. run android app and in settings enter your computer ip.

you may use this addin in any way you like as is, whatever is here on github is free to use on the agreement that none of it will be sold for profit in any way possible. if you want the source code for what is not on here, reach out to me at joshwaldner.sp@gmail.com
