// export const getScoreColor = (score: number) => {
//   if (score >= 80) return 'border-green-800 text-green-800'
//   if (score >= 50) return 'border-yellow-500 text-yellow-500'
//   return 'border-red-500 text-red-500'
// }

// export const renderPaginationButtons = (
//   total: number, 
//   current: number, 
//   handler: (page: number) => void
// ) => {
//   const buttons = []
//   const maxButtons = Math.min(total, 10);
  
//   for (let i = 0; i <= maxButtons; i++) {
//     let curr = i + (Math.floor(current/10) * 10);
//     if (curr > total) {
//       break;
//     }

//     if (curr !== 0) {
//       buttons.push(
//         <button
//           key={curr}
//           onClick={() => handler(curr)}
//           className={`mx-1 px-3 py-1 rounded ${
//             curr === current ? 'bg-pink-600 text-white' : 'bg-gray-200 text-gray-700'
//           }`}
//         >
//           {curr}
//         </button>
//       )
//     }
//   }
//   return buttons
// } 