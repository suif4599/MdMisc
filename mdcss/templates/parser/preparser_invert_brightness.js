markdown += `

<svg xmlns="http://www.w3.org/2000/svg" style="position: absolute; width: 0; height: 0; visibility: hidden;">
  <defs>
    <filter id="invert-brightness" color-interpolation-filters="sRGB">
      <feColorMatrix type="matrix" values="
        0.299   0.587   0.114   0  0
       -0.147  -0.289   0.436   0  0
        0.615  -0.515  -0.100   0  0
        0       0       0       1  0" />
      <feColorMatrix type="matrix" values="
        -1   0   0   0   1
         0   1   0   0   0
         0   0   1   0   0
         0   0   0   1   0" />
      <feColorMatrix type="matrix" values="
        1       0        1.13983  0   -0.569915
        1      -0.39465 -0.58060  0    0
        1       2.03211  0        0    0
        0       0        0        1    0" />
    </filter>
  </defs>
</svg>
`